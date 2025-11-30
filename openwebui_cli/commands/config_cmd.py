"""CLI configuration commands."""

import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ..config import (
    Config,
    ProfileConfig,
    get_config_path,
    load_config,
    save_config,
)

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def init(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize configuration file interactively."""
    config_path = get_config_path()

    if config_path.exists() and not force:
        console.print(f"[yellow]Config already exists at: {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    console.print("[bold]OpenWebUI CLI Configuration Setup[/bold]\n")

    # Get server URI
    uri = Prompt.ask(
        "Server URI",
        default="http://localhost:8080",
    )

    # Get default model
    default_model = Prompt.ask(
        "Default model (optional)",
        default="",
    )

    # Get output format
    default_format = Prompt.ask(
        "Default output format",
        choices=["text", "json", "yaml"],
        default="text",
    )

    # Build config
    config = Config(
        default_profile="default",
        profiles={
            "default": ProfileConfig(uri=uri),
        },
    )

    if default_model:
        config.defaults.model = default_model
    config.defaults.format = default_format

    # Save config
    save_config(config)
    console.print(f"\n[green]Configuration saved to: {config_path}[/green]")
    console.print("\nNext steps:")
    console.print("  1. Run 'openwebui auth login' to authenticate")
    console.print("  2. Run 'openwebui models list' to see available models")
    console.print("  3. Run 'openwebui chat send -m <model> -p \"Hello\"' to chat")


@app.command()
def show(ctx: typer.Context) -> None:
    """Show current configuration."""
    config_path = get_config_path()

    if not config_path.exists():
        console.print("[yellow]No config file found. Run 'openwebui config init' first.[/yellow]")
        raise typer.Exit(1)

    config = load_config()

    console.print(f"[bold]Config file:[/bold] {config_path}\n")

    # Show profiles
    table = Table(title="Profiles")
    table.add_column("Name", style="cyan")
    table.add_column("URI", style="green")
    table.add_column("Default", style="yellow")

    for name, profile in config.profiles.items():
        is_default = "✓" if name == config.default_profile else ""
        table.add_row(name, profile.uri, is_default)

    console.print(table)

    # Show defaults
    console.print("\n[bold]Defaults:[/bold]")
    console.print(f"  Model: {config.defaults.model or '(not set)'}")
    console.print(f"  Format: {config.defaults.format}")
    console.print(f"  Stream: {config.defaults.stream}")
    console.print(f"  Timeout: {config.defaults.timeout}s")


@app.command("set")
def set_value(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Config key (e.g., 'defaults.model')"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    config = load_config()

    parts = key.split(".")
    if len(parts) == 2:
        section, field = parts
        if section == "defaults":
            if field == "model":
                config.defaults.model = value
            elif field == "format":
                config.defaults.format = value
            elif field == "stream":
                config.defaults.stream = value.lower() in ("true", "1", "yes")
            elif field == "timeout":
                config.defaults.timeout = int(value)
            else:
                console.print(f"[red]Unknown defaults field: {field}[/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Unknown section: {section}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[red]Key format: section.field (e.g., 'defaults.model')[/red]")
        raise typer.Exit(1)

    save_config(config)
    console.print(f"[green]Set {key} = {value}[/green]")


@app.command("get")
def get_value(
    ctx: typer.Context,
    key: str = typer.Argument(..., help="Config key to get"),
) -> None:
    """Get a configuration value."""
    config = load_config()

    parts = key.split(".")
    if len(parts) == 2:
        section, field = parts
        if section == "defaults":
            value = getattr(config.defaults, field, None)
            if value is not None:
                console.print(str(value))
            else:
                console.print(f"[red]Unknown field: {field}[/red]")
                raise typer.Exit(1)
        elif section == "profiles":
            profile = config.profiles.get(field)
            if profile:
                console.print(f"uri: {profile.uri}")
            else:
                console.print(f"[red]Unknown profile: {field}[/red]")
                raise typer.Exit(1)
        else:
            console.print(f"[red]Unknown section: {section}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[red]Key format: section.field (e.g., 'defaults.model')[/red]")
        raise typer.Exit(1)
