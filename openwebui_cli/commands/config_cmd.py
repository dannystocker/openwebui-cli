"""CLI configuration commands."""

from urllib.parse import urlparse

import typer
import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from ..config import (
    Config,
    DefaultsConfig,
    OutputConfig,
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


def _validate_uri(uri: str) -> None:
    """Validate URI format."""
    parsed = urlparse(uri)
    if not parsed.scheme:
        raise ValueError("URI must have a scheme (e.g., http://, https://)")
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URI scheme must be 'http' or 'https', got '{parsed.scheme}'")


def _set_config_value(config: Config, key: str, value: str) -> None:
    """Set a configuration value using dot notation.

    Supports:
    - defaults.model
    - defaults.format
    - defaults.stream
    - defaults.timeout
    - output.colors
    - output.progress_bars
    - output.timestamps
    - profiles.<name>.uri
    """
    parts = key.split(".")

    try:
        if len(parts) == 2:
            section, field = parts

            if section == "defaults":
                _set_defaults_field(config.defaults, field, value)
            elif section == "output":
                _set_output_field(config.output, field, value)
            else:
                raise ValueError(f"Unknown section: {section}")
        elif len(parts) == 3:
            section, name, field = parts

            if section == "profiles":
                _set_profile_field(config, name, field, value)
            else:
                raise ValueError(f"Unknown section: {section}")
        else:
            msg = "Key format: section.field or profiles.<name>.uri (e.g., 'defaults.model')"
            raise ValueError(msg)
    except (ValueError, TypeError) as e:
        console.print(f"[red]Error setting {key}: {e}[/red]")
        raise typer.Exit(1)


def _set_defaults_field(defaults: DefaultsConfig, field: str, value: str) -> None:
    """Set a field in the defaults configuration."""
    if field == "model":
        defaults.model = value if value else None
    elif field == "format":
        if value not in ("text", "json", "yaml"):
            raise ValueError("format must be 'text', 'json', or 'yaml'")
        defaults.format = value
    elif field == "stream":
        defaults.stream = value.lower() in ("true", "1", "yes")
    elif field == "timeout":
        try:
            timeout = int(value)
            if timeout <= 0:
                raise ValueError("timeout must be positive")
            defaults.timeout = timeout
        except ValueError as e:
            raise ValueError(f"timeout must be a positive integer: {e}")
    else:
        raise ValueError(f"Unknown defaults field: {field}")


def _set_output_field(output: OutputConfig, field: str, value: str) -> None:
    """Set a field in the output configuration."""
    if field == "colors":
        output.colors = value.lower() in ("true", "1", "yes")
    elif field == "progress_bars":
        output.progress_bars = value.lower() in ("true", "1", "yes")
    elif field == "timestamps":
        output.timestamps = value.lower() in ("true", "1", "yes")
    else:
        raise ValueError(f"Unknown output field: {field}")


def _set_profile_field(config: Config, profile_name: str, field: str, value: str) -> None:
    """Set a field in a profile configuration."""
    if field != "uri":
        raise ValueError(f"Profile field must be 'uri', got '{field}'")

    _validate_uri(value)

    if profile_name not in config.profiles:
        config.profiles[profile_name] = ProfileConfig(uri=value)
    else:
        config.profiles[profile_name].uri = value


@app.command("set")
def set_value(
    ctx: typer.Context,
    key: str = typer.Argument(
        ...,
        help="Config key (e.g., 'defaults.model' or 'profiles.prod.uri')",
    ),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value.

    Examples:
        openwebui config set defaults.model mistral
        openwebui config set defaults.timeout 60
        openwebui config set profiles.prod.uri https://prod.example.com
        openwebui config set output.colors false
    """
    try:
        config = load_config()
    except yaml.YAMLError as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)

    _set_config_value(config, key, value)

    try:
        save_config(config)
        console.print(f"[green]Set {key} = {value}[/green]")
    except OSError as e:
        console.print(f"[red]Error saving config: {e}[/red]")
        raise typer.Exit(1)


def _get_config_value(config: Config, key: str) -> str:
    """Get a configuration value using dot notation.

    Supports:
    - defaults.model
    - defaults.format
    - defaults.stream
    - defaults.timeout
    - output.colors
    - output.progress_bars
    - output.timestamps
    - profiles.<name> (returns URI)
    - profiles.<name>.uri (returns URI)

    Returns the value as a string suitable for scripting.
    """
    parts = key.split(".")

    if len(parts) == 2:
        section, field = parts

        if section == "defaults":
            return _get_defaults_field(config.defaults, field)
        elif section == "output":
            return _get_output_field(config.output, field)
        elif section == "profiles":
            # profiles.<name> returns the URI
            return _get_profile_uri(config, field)
        else:
            raise KeyError(f"Unknown section: {section}")
    elif len(parts) == 3:
        section, name, field = parts

        if section == "profiles":
            return _get_profile_field(config, name, field)
        else:
            raise KeyError(f"Unknown section: {section}")
    else:
        raise KeyError("Key format: section.field or profiles.<name>.uri (e.g., 'defaults.model')")


def _get_defaults_field(defaults: DefaultsConfig, field: str) -> str:
    """Get a field from the defaults configuration."""
    if field == "model":
        return defaults.model or ""
    elif field == "format":
        return defaults.format
    elif field == "stream":
        return str(defaults.stream)
    elif field == "timeout":
        return str(defaults.timeout)
    else:
        raise KeyError(f"Unknown field: {field}")


def _get_output_field(output: OutputConfig, field: str) -> str:
    """Get a field from the output configuration."""
    if field == "colors":
        return str(output.colors)
    elif field == "progress_bars":
        return str(output.progress_bars)
    elif field == "timestamps":
        return str(output.timestamps)
    else:
        raise KeyError(f"Unknown field: {field}")


def _get_profile_uri(config: Config, profile_name: str) -> str:
    """Get the URI from a profile configuration."""
    profile = config.profiles.get(profile_name)
    if not profile:
        raise KeyError(f"Unknown profile: {profile_name}")
    return profile.uri


def _get_profile_field(config: Config, profile_name: str, field: str) -> str:
    """Get a field from a profile configuration."""
    profile = config.profiles.get(profile_name)
    if not profile:
        raise KeyError(f"Unknown profile: {profile_name}")

    if field == "uri":
        return profile.uri
    else:
        raise KeyError(f"Unknown field: {field}")


@app.command("get")
def get_value(
    ctx: typer.Context,
    key: str = typer.Argument(
        ...,
        help="Config key to get (e.g., 'defaults.model' or 'profiles.prod.uri')",
    ),
) -> None:
    """Get a configuration value.

    Returns just the value (no decorations) suitable for scripting.

    Examples:
        openwebui config get defaults.model
        openwebui config get defaults.timeout
        openwebui config get profiles.prod.uri
        openwebui config get output.colors
    """
    try:
        config = load_config()
    except yaml.YAMLError as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        raise typer.Exit(1)

    try:
        value = _get_config_value(config, key)
        console.print(value)
    except KeyError as e:
        console.print(f"[red]Error getting {key}: {e}[/red]")
        raise typer.Exit(1)
