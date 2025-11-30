"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from openwebui_cli.config import Config, ProfileConfig, load_config, save_config


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


def test_config_roundtrip(tmp_path, monkeypatch):
    """Test saving and loading config."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"

    # Monkey-patch the config path functions
    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    # Create and save config
    config = Config(
        default_profile="test",
        profiles={"test": ProfileConfig(uri="https://test.example.com")},
    )
    config.defaults.model = "test-model"

    save_config(config)

    # Load and verify
    loaded = load_config()
    assert loaded.default_profile == "test"
    assert loaded.profiles["test"].uri == "https://test.example.com"
    assert loaded.defaults.model == "test-model"
