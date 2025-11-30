"""Authentication commands."""

import typer
from rich.console import Console
from rich.prompt import Prompt

from ..config import get_effective_config
from ..errors import AuthError
from ..http import (
    create_client,
    delete_token,
    get_token,
    handle_request_error,
    handle_response,
    set_token,
)

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def login(
    ctx: typer.Context,
    username: str | None = typer.Option(None, "--username", "-u", help="Username or email"),
    password: str | None = typer.Option(
        None, "--password", "-p", help="Password (will prompt if not provided)"
    ),
) -> None:
    """Login to OpenWebUI instance."""
    obj = ctx.obj or {}
    uri, profile = get_effective_config(obj.get("profile"), obj.get("uri"))

    # Prompt for credentials if not provided
    if username is None:
        username = Prompt.ask("Username or email")
    if password is None:
        password = Prompt.ask("Password", password=True)

    try:
        with create_client(profile=profile, uri=uri) as client:
            response = client.post(
                "/api/v1/auths/signin",
                json={"email": username, "password": password},
            )
            data = handle_response(response)

            token = data.get("token")
            if not token:
                raise AuthError("No token received from server")

            # Store token in keyring
            set_token(profile, uri, token)

            user_name = data.get("name", username)
            console.print(f"[green]Successfully logged in as {user_name}[/green]")
            console.print(f"Token saved to system keyring for profile: {profile}")

    except Exception as e:
        handle_request_error(e)


@app.command()
def logout(ctx: typer.Context) -> None:
    """Logout and remove stored token."""
    obj = ctx.obj or {}
    uri, profile = get_effective_config(obj.get("profile"), obj.get("uri"))

    delete_token(profile, uri)
    console.print(f"[green]Logged out from profile: {profile}[/green]")


@app.command()
def whoami(ctx: typer.Context) -> None:
    """Show current user information."""
    obj = ctx.obj or {}

    try:
        with create_client(profile=obj.get("profile"), uri=obj.get("uri")) as client:
            response = client.get("/api/v1/auths/")
            data = handle_response(response)

            console.print(f"[bold]User:[/bold] {data.get('name', 'Unknown')}")
            console.print(f"[bold]Email:[/bold] {data.get('email', 'Unknown')}")
            console.print(f"[bold]Role:[/bold] {data.get('role', 'Unknown')}")

    except Exception as e:
        handle_request_error(e)


@app.command()
def token(
    ctx: typer.Context,
    show: bool = typer.Option(False, "--show", help="Show full token (careful!)"),
) -> None:
    """Show token information."""
    obj = ctx.obj or {}
    uri, profile = get_effective_config(obj.get("profile"), obj.get("uri"))

    stored_token = get_token(profile, uri)
    if stored_token:
        if show:
            console.print(f"[bold]Token:[/bold] {stored_token}")
        else:
            masked = (
                stored_token[:8] + "..." + stored_token[-4:] if len(stored_token) > 12 else "***"
            )
            console.print(f"[bold]Token:[/bold] {masked}")
        console.print(f"[bold]Profile:[/bold] {profile}")
        console.print(f"[bold]URI:[/bold] {uri}")
    else:
        console.print("[yellow]No token found. Run 'openwebui auth login' first.[/yellow]")


@app.command()
def refresh(ctx: typer.Context) -> None:
    """Refresh the authentication token."""
    obj = ctx.obj or {}

    try:
        with create_client(profile=obj.get("profile"), uri=obj.get("uri")) as client:
            response = client.post("/api/v1/auths/refresh")
            data = handle_response(response)

            uri, profile = get_effective_config(obj.get("profile"), obj.get("uri"))
            token = data.get("token")
            if token:
                set_token(profile, uri, token)
                console.print("[green]Token refreshed successfully[/green]")
            else:
                console.print("[yellow]No new token received[/yellow]")

    except Exception as e:
        handle_request_error(e)
