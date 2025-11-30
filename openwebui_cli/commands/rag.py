"""RAG (Retrieval-Augmented Generation) commands."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..http import create_client, handle_request_error, handle_response

app = typer.Typer(no_args_is_help=True)
console = Console()

# Sub-apps
files_app = typer.Typer(help="File operations")
collections_app = typer.Typer(help="Collection operations")

app.add_typer(files_app, name="files")
app.add_typer(collections_app, name="collections")


# Files commands
@files_app.command("list")
def list_files(ctx: typer.Context) -> None:
    """List uploaded files."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            response = client.get("/api/v1/files/")
            data = handle_response(response)

            files = data if isinstance(data, list) else data.get("files", [])

            if obj.get("format") == "json":
                console.print(json.dumps(files, indent=2))
            else:
                table = Table(title="Uploaded Files")
                table.add_column("ID", style="cyan")
                table.add_column("Filename", style="green")
                table.add_column("Size", style="yellow")

                for f in files:
                    file_id = f.get("id", "-")
                    filename = f.get("filename", f.get("name", "-"))
                    size = f.get("size", "-")
                    if isinstance(size, int):
                        size = f"{size / 1024:.1f} KB"
                    table.add_row(file_id, filename, str(size))

                console.print(table)

    except Exception as e:
        handle_request_error(e)


@files_app.command()
def upload(
    ctx: typer.Context,
    paths: list[Path] = typer.Argument(..., help="File path(s) to upload"),
    collection: str | None = typer.Option(None, "--collection", "-c", help="Add to collection"),
) -> None:
    """Upload file(s) for RAG."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            timeout=300,  # Longer timeout for uploads
        ) as client:
            for path in paths:
                if not path.exists():
                    console.print(f"[red]File not found: {path}[/red]")
                    continue

                with open(path, "rb") as f:
                    files = {"file": (path.name, f)}
                    response = client.post("/api/v1/files/", files=files)

                data = handle_response(response)
                file_id = data.get("id", "unknown")
                console.print(f"[green]Uploaded:[/green] {path.name} (id: {file_id})")

                # Add to collection if specified
                if collection and file_id != "unknown":
                    try:
                        client.post(
                            f"/api/v1/knowledge/{collection}/file/add",
                            json={"file_id": file_id},
                        )
                        console.print(f"  Added to collection: {collection}")
                    except Exception as e:
                        console.print(
                            f"  [yellow]Warning: Could not add to collection: {e}[/yellow]"
                        )

    except Exception as e:
        handle_request_error(e)


@files_app.command("delete")
def delete_file(
    ctx: typer.Context,
    file_id: str = typer.Argument(..., help="File ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an uploaded file."""
    obj = ctx.obj or {}

    if not force:
        confirm = typer.confirm(f"Delete file {file_id}?")
        if not confirm:
            raise typer.Abort()

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            response = client.delete(f"/api/v1/files/{file_id}")
            handle_response(response)
            console.print(f"[green]Deleted file: {file_id}[/green]")

    except Exception as e:
        handle_request_error(e)


# Collections commands
@collections_app.command("list")
def list_collections(ctx: typer.Context) -> None:
    """List knowledge collections."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            response = client.get("/api/v1/knowledge/")
            data = handle_response(response)

            collections = data if isinstance(data, list) else data.get("collections", [])

            if obj.get("format") == "json":
                console.print(json.dumps(collections, indent=2))
            else:
                table = Table(title="Knowledge Collections")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Description", style="yellow")

                for c in collections:
                    coll_id = c.get("id", "-")
                    name = c.get("name", "-")
                    desc = c.get("description", "-")[:50]
                    table.add_row(coll_id, name, desc)

                console.print(table)

    except Exception as e:
        handle_request_error(e)


@collections_app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Collection name"),
    description: str = typer.Option("", "--description", "-d", help="Collection description"),
) -> None:
    """Create a knowledge collection."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            response = client.post(
                "/api/v1/knowledge/",
                json={"name": name, "description": description},
            )
            data = handle_response(response)
            coll_id = data.get("id", "unknown")
            console.print(f"[green]Created collection:[/green] {name} (id: {coll_id})")

    except Exception as e:
        handle_request_error(e)


@collections_app.command("delete")
def delete_collection(
    ctx: typer.Context,
    collection_id: str = typer.Argument(..., help="Collection ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a knowledge collection."""
    obj = ctx.obj or {}

    if not force:
        confirm = typer.confirm(f"Delete collection {collection_id}?")
        if not confirm:
            raise typer.Abort()

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            response = client.delete(f"/api/v1/knowledge/{collection_id}")
            handle_response(response)
            console.print(f"[green]Deleted collection: {collection_id}[/green]")

    except Exception as e:
        handle_request_error(e)


# Search command
@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Search query"),
    collection: str = typer.Option(..., "--collection", "-c", help="Collection ID to search"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
) -> None:
    """Search within a collection (vector search)."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            response = client.post(
                f"/api/v1/knowledge/{collection}/query",
                json={"query": query, "k": top_k},
            )
            data = handle_response(response)

            results = data.get("results", data.get("documents", []))

            if obj.get("format") == "json":
                console.print(json.dumps(results, indent=2))
            else:
                console.print(f"[bold]Search results for:[/bold] {query}\n")
                for i, result in enumerate(results, 1):
                    content = result.get("content", result.get("text", str(result)))[:200]
                    score = result.get("score", result.get("distance", "-"))
                    console.print(f"[cyan]{i}.[/cyan] (score: {score})")
                    console.print(f"   {content}...")
                    console.print()

    except Exception as e:
        handle_request_error(e)
