"""Tests for configuration module and config CLI commands."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from openwebui_cli.config import (
    Config,
    DefaultsConfig,
    OutputConfig,
    ProfileConfig,
    Settings,
    get_config_dir,
    get_config_path,
    get_effective_config,
    load_config,
    save_config,
)
from openwebui_cli.main import app

runner = CliRunner()


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def mock_config_env(tmp_path, monkeypatch):
    """Use a temp config dir for all tests to avoid touching the real filesystem."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"

    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    # Clear environment variables to isolate tests
    monkeypatch.delenv("OPENWEBUI_URI", raising=False)
    monkeypatch.delenv("OPENWEBUI_TOKEN", raising=False)
    monkeypatch.delenv("OPENWEBUI_PROFILE", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    return config_dir, config_path


# ============================================================================
# Core Config Model Tests
# ============================================================================


def test_default_config():
    """Test default configuration values."""
    config = Config()

    assert config.version == 1
    assert config.default_profile == "default"
    assert "default" in config.profiles
    assert config.defaults.format == "text"
    assert config.defaults.stream is True
    assert config.defaults.timeout == 30


def test_profile_config():
    """Test profile configuration."""
    profile = ProfileConfig(uri="https://example.com")

    assert profile.uri == "https://example.com"


def test_defaults_config():
    """Test defaults configuration."""
    defaults = DefaultsConfig()

    assert defaults.model is None
    assert defaults.format == "text"
    assert defaults.stream is True
    assert defaults.timeout == 30


def test_output_config():
    """Test output configuration."""
    output = OutputConfig()

    assert output.colors is True
    assert output.progress_bars is True
    assert output.timestamps is False


def test_config_with_multiple_profiles():
    """Test config with multiple profiles."""
    config = Config(
        profiles={
            "default": ProfileConfig(uri="http://localhost:8080"),
            "prod": ProfileConfig(uri="https://prod.example.com"),
            "staging": ProfileConfig(uri="https://staging.example.com"),
        }
    )

    assert len(config.profiles) == 3
    assert config.profiles["default"].uri == "http://localhost:8080"
    assert config.profiles["prod"].uri == "https://prod.example.com"
    assert config.profiles["staging"].uri == "https://staging.example.com"


# ============================================================================
# Save and Load Tests
# ============================================================================


def test_config_roundtrip(mock_config_env):
    """Test saving and loading config."""
    config_dir, config_path = mock_config_env

    # Create and save config
    config = Config(
        default_profile="test",
        profiles={"test": ProfileConfig(uri="https://test.example.com")},
    )
    config.defaults.model = "test-model"

    save_config(config)

    # Verify file was created
    assert config_path.exists()

    # Load and verify
    loaded = load_config()
    assert loaded.default_profile == "test"
    assert loaded.profiles["test"].uri == "https://test.example.com"
    assert loaded.defaults.model == "test-model"


def test_load_config_missing_file(mock_config_env):
    """Test loading config when file doesn't exist."""
    config_dir, config_path = mock_config_env

    # Config should not exist
    assert not config_path.exists()

    # Load should return default config
    config = load_config()
    assert config.version == 1
    assert config.default_profile == "default"
    assert "default" in config.profiles


def test_save_config_creates_directory(mock_config_env):
    """Test that save_config creates parent directories."""
    config_dir, config_path = mock_config_env

    # Verify directory doesn't exist yet
    assert not config_dir.exists()

    config = Config()
    save_config(config)

    # Verify directory was created
    assert config_dir.exists()
    assert config_path.exists()


def test_config_yaml_format(mock_config_env):
    """Test that config is saved in proper YAML format."""
    config_dir, config_path = mock_config_env

    config = Config(
        default_profile="custom",
        profiles={"custom": ProfileConfig(uri="https://custom.example.com")},
    )
    config.defaults.model = "custom-model"
    config.defaults.timeout = 60

    save_config(config)

    # Read and verify YAML format
    with open(config_path) as f:
        data = yaml.safe_load(f)

    assert data["version"] == 1
    assert data["default_profile"] == "custom"
    assert data["profiles"]["custom"]["uri"] == "https://custom.example.com"
    assert data["defaults"]["model"] == "custom-model"
    assert data["defaults"]["timeout"] == 60


def test_load_config_with_partial_data(mock_config_env):
    """Test loading config with missing optional fields."""
    config_dir, config_path = mock_config_env
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write minimal YAML
    minimal_data = {
        "version": 1,
        "default_profile": "default",
        "profiles": {"default": {"uri": "http://localhost:8080"}},
    }

    with open(config_path, "w") as f:
        yaml.dump(minimal_data, f)

    # Load should work and fill in defaults
    config = load_config()
    assert config.version == 1
    assert config.defaults.format == "text"
    assert config.defaults.stream is True
    assert config.output.colors is True


def test_save_and_load_all_fields(mock_config_env):
    """Test saving and loading all configuration fields."""
    config_dir, config_path = mock_config_env

    config = Config(
        version=1,
        default_profile="main",
        profiles={
            "main": ProfileConfig(uri="https://main.example.com"),
            "backup": ProfileConfig(uri="https://backup.example.com"),
        },
        defaults=DefaultsConfig(
            model="gpt-4",
            format="json",
            stream=False,
            timeout=120,
        ),
        output=OutputConfig(
            colors=False,
            progress_bars=False,
            timestamps=True,
        ),
    )

    save_config(config)
    loaded = load_config()

    assert loaded.version == 1
    assert loaded.default_profile == "main"
    assert len(loaded.profiles) == 2
    assert loaded.defaults.model == "gpt-4"
    assert loaded.defaults.format == "json"
    assert loaded.defaults.stream is False
    assert loaded.defaults.timeout == 120
    assert loaded.output.colors is False
    assert loaded.output.progress_bars is False
    assert loaded.output.timestamps is True


# ============================================================================
# Effective Config Tests
# ============================================================================


def test_get_effective_config_defaults(mock_config_env):
    """Test effective config with all defaults."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    uri, profile = get_effective_config()

    assert uri == "http://localhost:8080"  # default profile default URI
    assert profile == "default"


def test_get_effective_config_with_profile_arg(mock_config_env):
    """Test effective config respects profile argument."""
    config_dir, config_path = mock_config_env
    config = Config(
        default_profile="default",
        profiles={
            "default": ProfileConfig(uri="http://localhost:8080"),
            "custom": ProfileConfig(uri="https://custom.example.com"),
        },
    )
    save_config(config)

    uri, profile = get_effective_config(profile="custom")

    assert uri == "https://custom.example.com"
    assert profile == "custom"


def test_get_effective_config_with_uri_arg(mock_config_env):
    """Test effective config respects URI argument."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    uri, profile = get_effective_config(uri="https://override.example.com")

    assert uri == "https://override.example.com"
    assert profile == "default"


def test_get_effective_config_precedence(mock_config_env, monkeypatch):
    """Test precedence: CLI flags > env vars > config file > defaults."""
    config_dir, config_path = mock_config_env

    config = Config(
        default_profile="config_profile",
        profiles={
            "config_profile": ProfileConfig(uri="http://from-config.example.com"),
        },
    )
    save_config(config)

    # Set environment variable
    monkeypatch.setenv("OPENWEBUI_PROFILE", "env_profile")
    monkeypatch.setenv("OPENWEBUI_URI", "http://from-env.example.com")

    # Create a new Settings instance (not cached)
    with patch("openwebui_cli.config.Settings") as mock_settings_cls:
        mock_settings = MagicMock()
        mock_settings.openwebui_profile = "env_profile"
        mock_settings.openwebui_uri = "http://from-env.example.com"
        mock_settings_cls.return_value = mock_settings

        # CLI flag should override everything
        uri, profile = get_effective_config(
            profile="cli_profile",
            uri="http://from-cli.example.com"
        )

        assert uri == "http://from-cli.example.com"
        assert profile == "cli_profile"


# ============================================================================
# Settings Tests
# ============================================================================


def test_settings_from_env(monkeypatch):
    """Test Settings loads from environment variables."""
    monkeypatch.setenv("OPENWEBUI_URI", "http://env.example.com")
    monkeypatch.setenv("OPENWEBUI_TOKEN", "env_token_123")
    monkeypatch.setenv("OPENWEBUI_PROFILE", "env_profile")

    settings = Settings()

    assert settings.openwebui_uri == "http://env.example.com"
    assert settings.openwebui_token == "env_token_123"
    assert settings.openwebui_profile == "env_profile"


def test_settings_empty_when_no_env(monkeypatch):
    """Test Settings are None when env vars not set."""
    monkeypatch.delenv("OPENWEBUI_URI", raising=False)
    monkeypatch.delenv("OPENWEBUI_TOKEN", raising=False)
    monkeypatch.delenv("OPENWEBUI_PROFILE", raising=False)

    settings = Settings()

    assert settings.openwebui_uri is None
    assert settings.openwebui_token is None
    assert settings.openwebui_profile is None


# ============================================================================
# CLI Command Tests - config init
# ============================================================================


def test_config_init_creates_file(mock_config_env):
    """Test config init command creates config file."""
    config_dir, config_path = mock_config_env

    result = runner.invoke(
        app,
        ["config", "init"],
        input="http://test.example.com\ntest-model\ntext\n",
    )

    assert result.exit_code == 0
    assert "Configuration saved" in result.stdout
    assert config_path.exists()


def test_config_init_with_defaults(mock_config_env):
    """Test config init with default values."""
    config_dir, config_path = mock_config_env

    # Just press enter to accept all defaults
    result = runner.invoke(
        app,
        ["config", "init"],
        input="\n\n\n",  # Use defaults for URI, model, format
    )

    assert result.exit_code == 0

    config = load_config()
    assert config.profiles["default"].uri == "http://localhost:8080"
    assert config.defaults.model is None
    assert config.defaults.format == "text"


def test_config_init_with_force(mock_config_env):
    """Test config init with --force overwrites existing config."""
    config_dir, config_path = mock_config_env

    # Create initial config
    config = Config(defaults=DefaultsConfig(model="old-model"))
    save_config(config)

    # Init with force should overwrite
    result = runner.invoke(
        app,
        ["config", "init", "--force"],
        input="http://new.example.com\n\njson\n",
    )

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.profiles["default"].uri == "http://new.example.com"
    assert loaded.defaults.format == "json"


def test_config_init_existing_without_force(mock_config_env):
    """Test config init fails when config exists without --force."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "init"],
    )

    assert result.exit_code == 1
    assert "Config already exists" in result.stdout or "already exists" in result.stdout


def test_config_init_f_short_flag(mock_config_env):
    """Test config init with -f short flag."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "init", "-f"],
        input="http://new.example.com\n\njson\n",
    )

    assert result.exit_code == 0


# ============================================================================
# CLI Command Tests - config show
# ============================================================================


def test_config_show_displays_profiles(mock_config_env):
    """Test config show displays profiles in table."""
    config_dir, config_path = mock_config_env

    config = Config(
        default_profile="main",
        profiles={
            "main": ProfileConfig(uri="https://main.example.com"),
            "backup": ProfileConfig(uri="https://backup.example.com"),
        },
    )
    save_config(config)

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "main" in result.stdout
    assert "backup" in result.stdout
    assert "https://main.example.com" in result.stdout
    assert "https://backup.example.com" in result.stdout


def test_config_show_displays_defaults(mock_config_env):
    """Test config show displays default settings."""
    config_dir, config_path = mock_config_env

    config = Config(
        defaults=DefaultsConfig(
            model="custom-model",
            format="json",
            timeout=60,
        ),
    )
    save_config(config)

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "custom-model" in result.stdout
    assert "json" in result.stdout
    assert "60" in result.stdout


def test_config_show_marks_default_profile(mock_config_env):
    """Test config show marks the default profile with indicator."""
    config_dir, config_path = mock_config_env

    config = Config(
        default_profile="prod",
        profiles={
            "dev": ProfileConfig(uri="http://dev.example.com"),
            "prod": ProfileConfig(uri="https://prod.example.com"),
        },
    )
    save_config(config)

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    # The checkmark should appear for prod profile
    assert "✓" in result.stdout


def test_config_show_no_config_file(mock_config_env):
    """Test config show fails gracefully when no config exists."""
    config_dir, config_path = mock_config_env

    # Don't create config file
    assert not config_path.exists()

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 1
    assert "No config file found" in result.stdout


def test_config_show_displays_config_path(mock_config_env):
    """Test config show displays the config file path."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    # The path may be split across lines due to terminal width,
    # so just check for the directory and config filename parts
    assert "openwebui" in result.stdout
    # Check for both continuous and split variants (including newline-split)
    assert "config.yaml" in result.stdout or (("config" in result.stdout or "config." in result.stdout) and "yaml" in result.stdout)


# ============================================================================
# CLI Command Tests - config set
# ============================================================================


def test_config_set_model(mock_config_env):
    """Test config set for model field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "defaults.model", "gpt-4"])

    assert result.exit_code == 0
    assert "Set defaults.model = gpt-4" in result.stdout

    loaded = load_config()
    assert loaded.defaults.model == "gpt-4"


def test_config_set_format(mock_config_env):
    """Test config set for format field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "defaults.format", "json"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.defaults.format == "json"


def test_config_set_timeout(mock_config_env):
    """Test config set for timeout field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "defaults.timeout", "120"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.defaults.timeout == 120


def test_config_set_stream_true(mock_config_env):
    """Test config set for stream field to true."""
    config_dir, config_path = mock_config_env

    config = Config(defaults=DefaultsConfig(stream=False))
    save_config(config)

    result = runner.invoke(app, ["config", "set", "defaults.stream", "true"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.defaults.stream is True


def test_config_set_stream_false_variants(mock_config_env):
    """Test config set for stream field with various false values."""
    config_dir, config_path = mock_config_env

    for false_val in ["false", "0", "no"]:
        save_config(Config(defaults=DefaultsConfig(stream=True)))

        result = runner.invoke(app, ["config", "set", "defaults.stream", false_val])

        assert result.exit_code == 0

        loaded = load_config()
        assert loaded.defaults.stream is False


def test_config_set_invalid_section(mock_config_env):
    """Test config set fails with invalid section."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "invalid.field", "value"])

    assert result.exit_code == 1
    assert "Unknown section" in result.stdout


def test_config_set_invalid_field(mock_config_env):
    """Test config set fails with invalid field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "defaults.invalid", "value"])

    assert result.exit_code == 1
    assert "Unknown defaults field" in result.stdout


def test_config_set_invalid_format(mock_config_env):
    """Test config set fails with invalid key format."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "invalid", "value"])

    assert result.exit_code == 1
    assert "Key format" in result.stdout


# ============================================================================
# CLI Command Tests - config get
# ============================================================================


def test_config_get_model(mock_config_env):
    """Test config get for model field."""
    config_dir, config_path = mock_config_env

    config = Config(defaults=DefaultsConfig(model="gpt-4"))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "defaults.model"])

    assert result.exit_code == 0
    assert "gpt-4" in result.stdout


def test_config_get_format(mock_config_env):
    """Test config get for format field."""
    config_dir, config_path = mock_config_env

    config = Config(defaults=DefaultsConfig(format="json"))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "defaults.format"])

    assert result.exit_code == 0
    assert "json" in result.stdout


def test_config_get_stream(mock_config_env):
    """Test config get for stream field."""
    config_dir, config_path = mock_config_env

    config = Config(defaults=DefaultsConfig(stream=False))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "defaults.stream"])

    assert result.exit_code == 0
    assert "False" in result.stdout


def test_config_get_timeout(mock_config_env):
    """Test config get for timeout field."""
    config_dir, config_path = mock_config_env

    config = Config(defaults=DefaultsConfig(timeout=60))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "defaults.timeout"])

    assert result.exit_code == 0
    assert "60" in result.stdout


def test_config_get_profile(mock_config_env):
    """Test config get for profile field."""
    config_dir, config_path = mock_config_env

    config = Config(
        profiles={"custom": ProfileConfig(uri="https://custom.example.com")}
    )
    save_config(config)

    result = runner.invoke(app, ["config", "get", "profiles.custom.uri"])

    assert result.exit_code == 0
    assert "https://custom.example.com" in result.stdout


def test_config_get_missing_field(mock_config_env):
    """Test config get fails for missing field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "defaults.nonexistent"])

    assert result.exit_code == 1
    assert "Unknown defaults field" in result.stdout or "Unknown field" in result.stdout


def test_config_get_missing_profile(mock_config_env):
    """Test config get fails for missing profile."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "profiles.nonexistent.uri"])

    assert result.exit_code == 1
    assert "Unknown profile" in result.stdout


def test_config_get_invalid_section(mock_config_env):
    """Test config get fails with invalid section."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "invalid.field"])

    assert result.exit_code == 1
    assert "Unknown section" in result.stdout


def test_config_get_invalid_format(mock_config_env):
    """Test config get fails with invalid key format."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "invalid"])

    assert result.exit_code == 1
    assert "Key format" in result.stdout


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_config_empty_file(mock_config_env):
    """Test loading config from empty YAML file."""
    config_dir, config_path = mock_config_env
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create empty file
    config_path.write_text("")

    config = load_config()

    # Should return default config
    assert config.version == 1
    assert config.default_profile == "default"


def test_config_corrupted_yaml(mock_config_env):
    """Test loading config from corrupted YAML."""
    config_dir, config_path = mock_config_env
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write invalid YAML
    config_path.write_text("{ invalid yaml: [")

    # Should raise an exception
    with pytest.raises(Exception):  # yaml.YAMLError
        load_config()


def test_get_config_dir_linux(monkeypatch):
    """Test get_config_dir on Linux/Unix."""
    monkeypatch.setattr("os.name", "posix")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

    with patch("openwebui_cli.config.Path.home") as mock_home:
        mock_home.return_value = Path("/home/user")
        config_dir = get_config_dir()

        assert "openwebui" in str(config_dir)
        assert ".config" in str(config_dir)


def test_get_config_dir_windows(monkeypatch):
    """Test get_config_dir on Windows."""
    # This test is skipped on non-Windows systems since WindowsPath
    # cannot be instantiated on POSIX systems
    if os.name != "nt":
        pytest.skip("Test only runs on Windows")

    monkeypatch.delenv("APPDATA", raising=False)

    with patch("openwebui_cli.config.Path.home") as mock_home:
        # Use PureWindowsPath to avoid instantiation issues
        from pathlib import PureWindowsPath
        mock_home.return_value = PureWindowsPath("C:\\Users\\user")
        config_dir = get_config_dir()

        assert "openwebui" in str(config_dir)


def test_config_set_with_special_characters(mock_config_env):
    """Test config set with special characters in value."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    special_value = "gpt-4-turbo-2024-04-09-preview"
    result = runner.invoke(
        app,
        ["config", "set", "defaults.model", special_value],
    )

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.defaults.model == special_value


def test_config_set_timeout_invalid_number(mock_config_env):
    """Test config set fails with invalid timeout value."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "set", "defaults.timeout", "not-a-number"],
    )

    assert result.exit_code == 1


def test_config_profiles_isolation(mock_config_env):
    """Test that profile changes don't affect other profiles."""
    config_dir, config_path = mock_config_env

    config = Config(
        profiles={
            "dev": ProfileConfig(uri="http://dev.example.com"),
            "prod": ProfileConfig(uri="https://prod.example.com"),
        },
    )
    save_config(config)

    # Change defaults which shouldn't affect profiles
    result = runner.invoke(app, ["config", "set", "defaults.model", "test-model"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.profiles["dev"].uri == "http://dev.example.com"
    assert loaded.profiles["prod"].uri == "https://prod.example.com"
    assert loaded.defaults.model == "test-model"


def test_get_effective_config_missing_profile(mock_config_env, monkeypatch):
    """Test get_effective_config with missing profile falls back to default."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    # Mock Settings to return missing profile
    with patch("openwebui_cli.config.Settings") as mock_settings_cls:
        mock_settings = MagicMock()
        mock_settings.openwebui_profile = "nonexistent"
        mock_settings.openwebui_uri = None
        mock_settings_cls.return_value = mock_settings

        uri, profile = get_effective_config()

        # Should use nonexistent profile name but default URI
        assert profile == "nonexistent"
        assert uri == "http://localhost:8080"  # default from default profile


# ============================================================================
# CLI Command Tests - config set output fields
# ============================================================================


def test_config_set_output_colors(mock_config_env):
    """Test config set for output colors field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "output.colors", "false"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.output.colors is False


def test_config_set_output_progress_bars(mock_config_env):
    """Test config set for output progress_bars field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "output.progress_bars", "false"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.output.progress_bars is False


def test_config_set_output_timestamps(mock_config_env):
    """Test config set for output timestamps field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "output.timestamps", "true"])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.output.timestamps is True


def test_config_get_output_colors(mock_config_env):
    """Test config get for output colors field."""
    config_dir, config_path = mock_config_env

    config = Config(output=OutputConfig(colors=False))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "output.colors"])

    assert result.exit_code == 0
    assert "False" in result.stdout


def test_config_get_output_progress_bars(mock_config_env):
    """Test config get for output progress_bars field."""
    config_dir, config_path = mock_config_env

    config = Config(output=OutputConfig(progress_bars=False))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "output.progress_bars"])

    assert result.exit_code == 0
    assert "False" in result.stdout


def test_config_get_output_timestamps(mock_config_env):
    """Test config get for output timestamps field."""
    config_dir, config_path = mock_config_env

    config = Config(output=OutputConfig(timestamps=True))
    save_config(config)

    result = runner.invoke(app, ["config", "get", "output.timestamps"])

    assert result.exit_code == 0
    assert "True" in result.stdout


# ============================================================================
# CLI Command Tests - config set profile URI
# ============================================================================


def test_config_set_profile_uri(mock_config_env):
    """Test config set for profile URI."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "set", "profiles.production.uri", "https://prod.example.com"],
    )

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.profiles["production"].uri == "https://prod.example.com"


def test_config_set_profile_uri_invalid_scheme(mock_config_env):
    """Test config set fails for profile URI with invalid scheme."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "set", "profiles.test.uri", "ftp://invalid.example.com"],
    )

    assert result.exit_code == 1
    assert "scheme" in result.stdout.lower()


def test_config_set_profile_uri_no_scheme(mock_config_env):
    """Test config set fails for profile URI without scheme."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "set", "profiles.test.uri", "invalid.example.com"],
    )

    assert result.exit_code == 1
    assert "scheme" in result.stdout.lower()


def test_config_get_profile_uri_2part_format(mock_config_env):
    """Test config get with 2-part profile key format."""
    config_dir, config_path = mock_config_env

    config = Config(
        profiles={"prod": ProfileConfig(uri="https://prod.example.com")}
    )
    save_config(config)

    result = runner.invoke(app, ["config", "get", "profiles.prod"])

    assert result.exit_code == 0
    assert "https://prod.example.com" in result.stdout


# ============================================================================
# Additional CLI Command Tests - edge cases
# ============================================================================


def test_config_set_format_invalid_value(mock_config_env):
    """Test config set fails with invalid format value."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "defaults.format", "invalid"])

    assert result.exit_code == 1
    assert "format" in result.stdout.lower()


def test_config_set_invalid_output_field(mock_config_env):
    """Test config set fails with invalid output field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "set", "output.invalid", "true"])

    assert result.exit_code == 1
    assert "Unknown output field" in result.stdout


def test_config_set_invalid_profile_field(mock_config_env):
    """Test config set fails with invalid profile field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(
        app,
        ["config", "set", "profiles.test.invalid", "value"],
    )

    assert result.exit_code == 1
    assert "uri" in result.stdout.lower()


def test_config_get_invalid_output_field(mock_config_env):
    """Test config get fails with invalid output field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "output.invalid"])

    assert result.exit_code == 1
    assert "Unknown field" in result.stdout


def test_config_get_invalid_profile_field(mock_config_env):
    """Test config get fails with invalid profile field."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "profiles.default.invalid"])

    assert result.exit_code == 1
    assert "Unknown field" in result.stdout


def test_config_set_empty_model(mock_config_env):
    """Test config set with empty string clears model."""
    config_dir, config_path = mock_config_env

    config = Config(defaults=DefaultsConfig(model="gpt-4"))
    save_config(config)

    result = runner.invoke(app, ["config", "set", "defaults.model", ""])

    assert result.exit_code == 0

    loaded = load_config()
    assert loaded.defaults.model is None


def test_config_get_model_when_not_set(mock_config_env):
    """Test config get returns empty string for unset model."""
    config_dir, config_path = mock_config_env
    save_config(Config())

    result = runner.invoke(app, ["config", "get", "defaults.model"])

    assert result.exit_code == 0
    # Should return empty string or nothing visible
    assert result.stdout.strip() == ""
