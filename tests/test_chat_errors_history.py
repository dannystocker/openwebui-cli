"""Tests for history file error conditions in chat commands."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from openwebui_cli.main import app

runner = CliRunner()


@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    """Mock configuration for testing."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"

    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    # Create default config
    from openwebui_cli.config import Config, save_config
    config = Config()
    save_config(config)

    return config_path


@pytest.fixture
def mock_keyring(monkeypatch):
    """Mock keyring for testing."""
    token_store = {}

    def get_password(service, key):
        return token_store.get(f"{service}:{key}")

    def set_password(service, key, password):
        token_store[f"{service}:{key}"] = password

    monkeypatch.setattr("keyring.get_password", get_password)
    monkeypatch.setattr("keyring.set_password", set_password)


def test_missing_history_file(mock_config, mock_keyring):
    """Test nonexistent history file raises appropriate error."""
    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", "/nonexistent/path/to/history.json",
        ],
    )

    assert result.exit_code == 2
    assert "not found" in result.output.lower() or "does not exist" in result.output.lower()
    assert "history" in result.output.lower()


def test_invalid_json_history_file(tmp_path, mock_config, mock_keyring):
    """Test history file with invalid JSON raises appropriate error."""
    # Create temp file with invalid JSON
    history_file = tmp_path / "invalid.json"
    with open(history_file, "w") as f:
        f.write("{bad json content")

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", str(history_file),
        ],
    )

    assert result.exit_code == 2
    assert "json" in result.output.lower() or "parse" in result.output.lower()


def test_history_file_wrong_shape_dict_without_messages(tmp_path, mock_config, mock_keyring):
    """Test history file with valid JSON but wrong structure (dict without 'messages' key)."""
    # Create temp file with valid JSON but wrong shape
    history_file = tmp_path / "wrong_shape.json"
    with open(history_file, "w") as f:
        json.dump({"not": "a list", "wrong": "structure"}, f)

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", str(history_file),
        ],
    )

    assert result.exit_code == 2
    assert "array" in result.output.lower() or "list" in result.output.lower() or "messages" in result.output.lower()


def test_history_file_wrong_shape_string(tmp_path, mock_config, mock_keyring):
    """Test history file with valid JSON but wrong type (string instead of array/object)."""
    # Create temp file with valid JSON string
    history_file = tmp_path / "string_content.json"
    with open(history_file, "w") as f:
        json.dump("just a string", f)

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", str(history_file),
        ],
    )

    assert result.exit_code == 2
    assert "array" in result.output.lower() or "list" in result.output.lower() or "messages" in result.output.lower()


def test_history_file_wrong_shape_number(tmp_path, mock_config, mock_keyring):
    """Test history file with valid JSON but wrong type (number instead of array/object)."""
    # Create temp file with valid JSON number
    history_file = tmp_path / "number_content.json"
    with open(history_file, "w") as f:
        json.dump(42, f)

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", str(history_file),
        ],
    )

    assert result.exit_code == 2
    assert "array" in result.output.lower() or "list" in result.output.lower() or "messages" in result.output.lower()


def test_history_file_empty_json_object(tmp_path, mock_config, mock_keyring):
    """Test history file with empty JSON object (no messages key)."""
    # Create temp file with empty object
    history_file = tmp_path / "empty_object.json"
    with open(history_file, "w") as f:
        json.dump({}, f)

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", str(history_file),
        ],
    )

    assert result.exit_code == 2
    assert "array" in result.output.lower() or "list" in result.output.lower() or "messages" in result.output.lower()


def test_history_file_empty_array(tmp_path, mock_config, mock_keyring):
    """Test history file with empty array (should succeed with empty history)."""
    # Create temp file with empty array
    history_file = tmp_path / "empty_array.json"
    with open(history_file, "w") as f:
        json.dump([], f)

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response with empty history"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "-m", "test-model",
                "-p", "Hello",
                "--history-file", str(history_file),
                "--no-stream"
            ],
        )

        assert result.exit_code == 0


def test_history_file_with_messages_key(tmp_path, mock_config, mock_keyring):
    """Test history file with object containing 'messages' key (should succeed)."""
    # Create temp file with object containing messages key
    history_file = tmp_path / "with_messages.json"
    history_data = {
        "messages": [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
        ]
    }
    with open(history_file, "w") as f:
        json.dump(history_data, f)

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response with message history"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "-m", "test-model",
                "-p", "What about 3+3?",
                "--history-file", str(history_file),
                "--no-stream"
            ],
        )

        assert result.exit_code == 0


def test_history_file_with_direct_array(tmp_path, mock_config, mock_keyring):
    """Test history file with direct array of messages (should succeed)."""
    # Create temp file with direct array
    history_file = tmp_path / "direct_array.json"
    history_data = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
    ]
    with open(history_file, "w") as f:
        json.dump(history_data, f)

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response with direct array history"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "-m", "test-model",
                "-p", "What about 5+5?",
                "--history-file", str(history_file),
                "--no-stream"
            ],
        )

        assert result.exit_code == 0


def test_history_file_malformed_utf8(tmp_path, mock_config, mock_keyring):
    """Test history file with invalid UTF-8 encoding."""
    # Create temp file with invalid UTF-8
    history_file = tmp_path / "invalid_utf8.json"
    with open(history_file, "wb") as f:
        # Write invalid UTF-8 bytes
        f.write(b'\x80\x81\x82')

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "-m", "test-model",
            "-p", "Hello",
            "--history-file", str(history_file),
        ],
    )

    # Should fail with error code 2
    assert result.exit_code == 2
