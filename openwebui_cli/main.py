"""Main CLI entry point."""

import typer
from rich.console import Console

from . import __version__
from .commands import auth, chat, config_cmd, models, rag, admin

# Create main app
app = typer.Typer(
    name="openwebui",
    help="Official CLI for OpenWebUI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

# Create console for rich output
console = Console()

# Register sub-commands
app.add_typer(auth.app, name="auth", help="Authentication commands")
app.add_typer(chat.app, name="chat", help="Chat operations")
app.add_typer(models.app, name="models", help="Model management")
app.add_typer(rag.app, name="rag", help="RAG file and collection operations")
app.add_typer(admin.app, name="admin", help="Admin operations (requires admin role)")
app.add_typer(config_cmd.app, name="config", help="CLI configuration")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
    profile: str | None = typer.Option(None, "--profile", "-P", help="Use named profile"),
    uri: str | None = typer.Option(None, "--uri", "-U", help="Server URI"),
    format: str | None = typer.Option(None, "--format", "-f", help="Output format: text, json, yaml"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output"),
    verbose: bool = typer.Option(False, "--verbose", "--debug", help="Enable debug logging"),
    timeout: int | None = typer.Option(None, "--timeout", "-t", help="Request timeout in seconds"),
) -> None:
    """OpenWebUI CLI - interact with your OpenWebUI instance from the command line."""
    if version:
        console.print(f"openwebui-cli version {__version__}")
        raise typer.Exit()

    # Store global options in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile
    ctx.obj["uri"] = uri
    ctx.obj["format"] = format or "text"
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["timeout"] = timeout


if __name__ == "__main__":
    app()
