"""Admin commands (requires admin role)."""

import json
from typing import Any

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
            token=obj.get("token"),
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


def _check_admin_role(user_data: dict[str, Any]) -> None:
    """Check if current user has admin role, raise AuthError if not."""
    if user_data.get("role") != "admin":
        user_name = user_data.get("name", "Unknown")
        user_role = user_data.get("role", "Unknown")
        raise AuthError(
            f"Admin role required. Your current user is '{user_name}' "
            f"with role: [{user_role}]"
        )


def _get_current_user(client: Any) -> dict[str, Any]:
    """Fetch current user information."""
    response = client.get("/api/v1/auths/")
    return handle_response(response)


@app.command()
def users(ctx: typer.Context) -> None:
    """List users (requires admin role)."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            # Check if user is admin
            user_data = _get_current_user(client)
            _check_admin_role(user_data)

            # Fetch users list
            response = client.get("/api/v1/users/")
            users_data = handle_response(response)

            # Extract users array (handle different response formats)
            if isinstance(users_data, dict):
                users_list = users_data.get("data", users_data)
            else:
                users_list = users_data
            if not isinstance(users_list, list):
                users_list = [users_data]

            if obj.get("format") == "json":
                console.print(json.dumps(users_list, indent=2))
            else:
                table = Table(title="OpenWebUI Users")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Email", style="yellow")
                table.add_column("Role", style="magenta")

                for user in users_list:
                    user_id = user.get("id", "-")
                    name = user.get("name", user.get("username", "-"))
                    email = user.get("email", "-")
                    role = user.get("role", "-")

                    table.add_row(user_id, name, email, role)

                console.print(table)

    except AuthError:
        raise
    except Exception as e:
        handle_request_error(e)


@app.command()
def config(ctx: typer.Context) -> None:
    """Show server configuration (requires admin role)."""
    obj = ctx.obj or {}

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            token=obj.get("token"),
        ) as client:
            # Check if user is admin
            user_data = _get_current_user(client)
            _check_admin_role(user_data)

            # Try to fetch config from admin endpoint
            try:
                response = client.get("/api/v1/admin/config")
                config_data = handle_response(response)
            except Exception:
                # Fallback: basic server info
                config_data = {
                    "status": "connected",
                    "user": user_data.get("name"),
                    "role": user_data.get("role"),
                }

            if obj.get("format") == "json":
                console.print(json.dumps(config_data, indent=2))
            else:
                table = Table(title="Server Configuration")
                table.add_column("Setting", style="cyan")
                table.add_column("Value", style="green")

                for key, value in config_data.items():
                    table.add_row(str(key), str(value))

                console.print(table)

    except AuthError:
        raise
    except Exception as e:
        handle_request_error(e)
