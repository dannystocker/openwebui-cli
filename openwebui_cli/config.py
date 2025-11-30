"""Configuration management for OpenWebUI CLI."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


def get_config_dir() -> Path:
    """Get the configuration directory path (XDG-compliant)."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:  # Unix/Linux/macOS
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "openwebui"


def get_config_path() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / "config.yaml"


class ProfileConfig(BaseModel):
    """Configuration for a single server profile."""

    uri: str = "http://localhost:8080"
    # Token stored in keyring, not in config file


class DefaultsConfig(BaseModel):
    """Default settings for CLI commands."""

    model: str | None = None
    format: str = "text"
    stream: bool = True
    timeout: int = 30


class OutputConfig(BaseModel):
    """Output formatting preferences."""

    colors: bool = True
    progress_bars: bool = True
    timestamps: bool = False


class Config(BaseModel):
    """Main configuration model."""

    version: int = 1
    default_profile: str = "default"
    profiles: dict[str, ProfileConfig] = Field(default_factory=lambda: {"default": ProfileConfig()})
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


class Settings(BaseSettings):
    """Environment-based settings that override config file."""

    model_config = ConfigDict(env_prefix="", case_sensitive=False)

    openwebui_uri: str | None = None
    openwebui_token: str | None = None
    openwebui_profile: str | None = None


def load_config() -> Config:
    """Load configuration from file, with defaults for missing values."""
    config_path = get_config_path()

    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return Config(**data)
    else:
        return Config()


def save_config(config: Config) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)


def get_effective_config(
    profile: str | None = None,
    uri: str | None = None,
) -> tuple[str, str | None]:
    """
    Get effective URI and profile name, respecting precedence:
    CLI flags > env vars > config file > defaults
    """
    config = load_config()
    settings = Settings()

    # Determine profile
    effective_profile = profile or settings.openwebui_profile or config.default_profile

    # Get profile config
    profile_config = config.profiles.get(effective_profile, ProfileConfig())

    # Determine URI with precedence
    effective_uri = uri or settings.openwebui_uri or profile_config.uri

    return effective_uri, effective_profile
