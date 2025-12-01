"""RAG (Retrieval-Augmented Generation) commands."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..errors import UsageError
from ..http import create_client, handle_request_error, handle_response

app = typer.Typer(no_args_is_help=True)
console = Console()

# Sub-apps
files_app = typer.Typer(help="File operations")
collections_app = typer.Typer(help="Collection operations")

app.add_typer(files_app, name="files")
app.add_typer(collections_app, name="collections")

# Constants
MAX_FILE_SIZE_MB = 100
MIN_SEARCH_QUERY_LENGTH = 3
MIN_COLLECTION_NAME_LENGTH = 1


# Files commands
@files_app.command("list")
def list_files(ctx: typer.Context) -> None:
    """List uploaded files."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            response = client.get("/api/v1/files/")
            data = handle_response(response)

            files = data if isinstance(data, list) else data.get("files", [])

            if not files:
                console.print("[yellow]No files found.[/yellow]")
                return

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

    if not paths:
        raise UsageError("At least one file path is required.")

    successful_uploads = 0
    failed_uploads = 0

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
            timeout=300,  # Longer timeout for uploads
        ) as client:
            for path in paths:
                # Check file existence
                if not path.exists():
                    console.print(f"[red]Error: File not found: {path}[/red]")
                    failed_uploads += 1
                    continue

                # Validate file is readable
                if not path.is_file():
                    console.print(f"[red]Error: Not a file: {path}[/red]")
                    failed_uploads += 1
                    continue

                # Check file size
                file_size_mb = path.stat().st_size / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    console.print(
                        f"[yellow]Warning: File '{path.name}' is {file_size_mb:.1f}MB "
                        f"(exceeds {MAX_FILE_SIZE_MB}MB limit). "
                        f"Upload may fail or be slow.[/yellow]"
                    )

                try:
                    # Show progress for large files
                    if file_size_mb > 10:
                        console.print(f"Uploading: {path.name} ({file_size_mb:.1f}MB)...")

                    with open(path, "rb") as f:
                        files = {"file": (path.name, f)}
                        response = client.post("/api/v1/files/", files=files)

                    data = handle_response(response)
                    file_id = data.get("id", "unknown")

                    if file_id == "unknown":
                        console.print(
                            "[yellow]Warning: Upload succeeded but got no file ID[/yellow]"
                        )
                        failed_uploads += 1
                        continue

                    console.print(f"[green]Uploaded:[/green] {path.name} (id: {file_id})")
                    successful_uploads += 1

                    # Add to collection if specified
                    if collection:
                        try:
                            response = client.post(
                                f"/api/v1/knowledge/{collection}/file/add",
                                json={"file_id": file_id},
                            )
                            handle_response(response)
                            console.print(f"  [green]Added to collection: {collection}[/green]")
                        except Exception as coll_error:
                            console.print(
                                f"  [red]Error: Could not add to collection "
                                f"'{collection}': {coll_error}[/red]"
                            )

                except Exception as upload_error:
                    console.print(f"[red]Error uploading '{path.name}': {upload_error}[/red]")
                    console.print("  Tip: Check file permissions and server logs.")
                    failed_uploads += 1

    except Exception as e:
        handle_request_error(e)

    # Summary
    if successful_uploads > 0 or failed_uploads > 0:
        console.print(
            f"\n[bold]Summary:[/bold] {successful_uploads} successful, {failed_uploads} failed"
        )


@files_app.command("delete")
def delete_file(
    ctx: typer.Context,
    file_id: str = typer.Argument(..., help="File ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete an uploaded file."""
    obj = ctx.obj or {}

    if not file_id or not file_id.strip():
        raise UsageError("File ID cannot be empty.")

    if not force:
        confirm = typer.confirm(f"Delete file {file_id}?")
        if not confirm:
            raise typer.Abort()

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
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
            token=obj.get("token"),
        ) as client:
            response = client.get("/api/v1/knowledge/")
            data = handle_response(response)

            collections = data if isinstance(data, list) else data.get("collections", [])

            if not collections:
                console.print(
                    "[yellow]No collections found. "
                    "Create one with: openwebui rag collections create[/yellow]"
                )
                return

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
                    desc = c.get("description", "-")[:50] if c.get("description") else "-"
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

    # Validate collection name
    if not name or not name.strip():
        raise UsageError("Collection name cannot be empty.")

    if len(name.strip()) < MIN_COLLECTION_NAME_LENGTH:
        raise UsageError(
            f"Collection name must be at least {MIN_COLLECTION_NAME_LENGTH} "
            f"character(s)."
        )

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            response = client.post(
                "/api/v1/knowledge/",
                json={"name": name.strip(), "description": description.strip()},
            )
            data = handle_response(response)
            coll_id = data.get("id", "unknown")

            if coll_id == "unknown":
                console.print("[yellow]Warning: Collection created but got no ID[/yellow]")
            else:
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

    if not collection_id or not collection_id.strip():
        raise UsageError("Collection ID cannot be empty.")

    if not force:
        confirm = typer.confirm(f"Delete collection {collection_id}? This cannot be undone.")
        if not confirm:
            console.print("[yellow]Delete cancelled.[/yellow]")
            return

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
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

    # Validate search query
    if not query or not query.strip():
        raise UsageError("Search query cannot be empty.")

    if len(query.strip()) < MIN_SEARCH_QUERY_LENGTH:
        raise UsageError(f"Search query must be at least {MIN_SEARCH_QUERY_LENGTH} characters.")

    # Validate collection ID
    if not collection or not collection.strip():
        raise UsageError("Collection ID is required (use --collection or -c option).")

    # Validate top_k
    if top_k < 1:
        raise UsageError("Number of results (--top-k) must be at least 1.")

    if top_k > 100:
        console.print("[yellow]Warning: Requesting more than 100 results may be slow.[/yellow]")

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            response = client.post(
                f"/api/v1/knowledge/{collection.strip()}/query",
                json={"query": query.strip(), "k": top_k},
            )
            data = handle_response(response)

            results = data.get("results", data.get("documents", []))

            if not results:
                console.print(f"[yellow]No results found for query: '{query}'[/yellow]")
                console.print("[dim]Try adjusting your search query and try again.[/dim]")
                return

            if obj.get("format") == "json":
                console.print(json.dumps(results, indent=2))
            else:
                num_results = len(results)
                console.print(
                    f"[bold]Search results for:[/bold] {query} ({num_results} result(s))\n"
                )
                for i, result in enumerate(results, 1):
                    content = result.get("content", result.get("text", str(result)))[:200]
                    score = result.get("score", result.get("distance", "-"))
                    metadata = result.get("metadata", {})
                    source = metadata.get("source", "-") if isinstance(metadata, dict) else "-"

                    console.print(f"[cyan]{i}.[/cyan] (score: {score})")
                    if source and source != "-":
                        console.print(f"   [dim]Source: {source}[/dim]")
                    console.print(f"   {content}...")
                    console.print()

    except Exception as e:
        handle_request_error(e)
