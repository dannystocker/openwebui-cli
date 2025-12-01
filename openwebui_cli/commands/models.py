"""Model management commands."""

import json

import typer
from rich.console import Console
from rich.table import Table

from ..http import create_client, handle_request_error, handle_response

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command("list")
def list_models(
    ctx: typer.Context,
    provider: str | None = typer.Option(None, "--provider", "-p", help="Filter by provider"),
) -> None:
    """List available models."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            response = client.get("/api/models")
            data = handle_response(response)

            models = data.get("data", data.get("models", []))

            if obj.get("format") == "json":
                console.print(json.dumps(models, indent=2))
            else:
                table = Table(title="Available Models")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Provider", style="yellow")

                for model in models:
                    model_id = model.get("id", model.get("model", "Unknown"))
                    name = model.get("name", model_id)
                    model_provider = model.get("owned_by", model.get("provider", "-"))

                    if provider and provider.lower() not in model_provider.lower():
                        continue

                    table.add_row(model_id, name, model_provider)

                console.print(table)

    except Exception as e:
        handle_request_error(e)


@app.command()
def info(
    ctx: typer.Context,
    model_id: str = typer.Argument(..., help="Model ID to inspect"),
) -> None:
    """Show model details."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            response = client.get(f"/api/models/{model_id}")
            data = handle_response(response)

            if obj.get("format") == "json":
                console.print(json.dumps(data, indent=2))
            else:
                console.print(f"[bold]Model:[/bold] {data.get('id', model_id)}")
                console.print(f"[bold]Name:[/bold] {data.get('name', '-')}")
                console.print(f"[bold]Provider:[/bold] {data.get('owned_by', '-')}")

                if params := data.get("parameters"):
                    console.print(f"[bold]Parameters:[/bold] {params}")
                if context := data.get("context_length"):
                    console.print(f"[bold]Context Length:[/bold] {context}")

    except Exception as e:
        handle_request_error(e)


@app.command()
def pull(
    ctx: typer.Context,
    model_name: str = typer.Argument(..., help="Model name to pull"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-pull existing models"),
    progress: bool = typer.Option(True, "--progress/--no-progress", help="Show download progress"),
) -> None:
    """Pull/download a model from registry."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            # Check if model already exists
            if not force:
                try:
                    existing = client.get(f"/api/models/{model_name}")
                    if existing.status_code == 200:
                        console.print(
                            f"[yellow]Model '{model_name}' already exists. "
                            "Use --force to re-pull.[/yellow]"
                        )
                        return
                except Exception:
                    # Model doesn't exist, proceed with pull
                    pass

            # Pull the model
            if progress:
                console.print(f"[cyan]Pulling model: {model_name}...[/cyan]")

            response = client.post(
                "/api/models/pull",
                json={"name": model_name},
            )
            data = handle_response(response)

            # Check if pull was successful
            if data.get("status") == "success" or response.status_code == 200:
                console.print(f"[green]Successfully pulled model: {model_name}[/green]")
            else:
                # API returned 200 but status indicates potential issue
                error_msg = data.get("message", data.get("error", "Unknown error"))
                console.print(f"[yellow]Pull completed with status: {error_msg}[/yellow]")

    except Exception as e:
        handle_request_error(e)


@app.command()
def delete(
    ctx: typer.Context,
    model_name: str = typer.Argument(..., help="Model name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete a model from the system."""
    obj = ctx.obj or {}

    if not force:
        confirm = typer.confirm(f"Delete model '{model_name}'?", default=False)
        if not confirm:
            raise typer.Abort()

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            response = client.delete(f"/api/models/{model_name}")
            handle_response(response)
            console.print(f"[green]Successfully deleted model: {model_name}[/green]")

    except Exception as e:
        handle_request_error(e)
