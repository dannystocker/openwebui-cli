"""Admin commands (requires admin role)."""

import json

import typer
from rich.console import Console
from rich.table import Table

from ..errors import AuthError
from ..http import create_client, handle_request_error, handle_response

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def stats(
    ctx: typer.Context,
    period: str = typer.Option("day", "--period", "-p", help="Period: day, week, month"),
) -> None:
    """Show usage statistics."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
        ) as client:
            # Try to get stats from various endpoints
            try:
                response = client.get("/api/v1/admin/stats")
                data = handle_response(response)
            except Exception:
                # Fallback to basic info
                response = client.get("/api/v1/auths/")
                user_data = handle_response(response)

                if user_data.get("role") != "admin":
                    user_name = user_data.get("name")
                    user_role = user_data.get("role")
                    raise AuthError(
                        f"Admin command requires admin privileges; "
                        f"your current user is '{user_name}' with role: [{user_role}]"
                    )

                # Build basic stats
                data = {
                    "user": user_data.get("name"),
                    "role": user_data.get("role"),
                    "status": "connected",
                }

            if obj.get("format") == "json":
                console.print(json.dumps(data, indent=2))
            else:
                table = Table(title="Server Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                for key, value in data.items():
                    table.add_row(str(key), str(value))

                console.print(table)

    except AuthError:
        raise
    except Exception as e:
        handle_request_error(e)


@app.command()
def users(ctx: typer.Context) -> None:
    """List users (v1.1 feature - placeholder)."""
    console.print("[yellow]Admin users will be available in v1.1[/yellow]")


@app.command()
def config(ctx: typer.Context) -> None:
    """Server configuration (v1.1 feature - placeholder)."""
    console.print("[yellow]Admin config will be available in v1.1[/yellow]")
