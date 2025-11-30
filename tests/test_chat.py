"""Tests for chat commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from typer.testing import CliRunner

from openwebui_cli.main import app

runner = CliRunner()


class MockStreamResponse:
    """Mock streaming response for testing."""

    def __init__(self, lines, status_code=200):
        self.lines = lines
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_lines(self):
        """Yield lines one by one."""
        for line in self.lines:
            yield line


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


def test_chat_send_streaming(mock_config, mock_keyring):
    """Test streaming chat response."""
    # Mock streaming response
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        'data: {"choices": [{"delta": {"content": "!"}}]}',
        "data: [DONE]",
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponse(streaming_lines)
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        assert result.exit_code == 0
        assert "Hello world!" in result.stdout


def test_chat_send_no_stream(mock_config, mock_keyring):
    """Test non-streaming chat response."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "This is a test response"
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
            ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
        )

        assert result.exit_code == 0
        assert "This is a test response" in result.stdout


def test_chat_send_with_system_prompt(mock_config, mock_keyring):
    """Test chat with system prompt."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response with system prompt"
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
                "-s", "You are a helpful assistant",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0


def test_chat_send_with_history_file(tmp_path, mock_config, mock_keyring):
    """Test chat with history file."""
    # Create history file
    history_file = tmp_path / "history.json"
    history = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "4"},
    ]
    with open(history_file, "w") as f:
        json.dump(history, f)

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Continuing conversation"
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


def test_chat_send_stdin(mock_config, mock_keyring):
    """Test chat with stdin input."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response from stdin"
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
            ["chat", "send", "-m", "test-model", "--no-stream"],
            input="Hello from stdin\n",
        )

        assert result.exit_code == 0


def test_chat_send_json_output(mock_config, mock_keyring):
    """Test chat with JSON output format."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Test"}}]}',
        "data: [DONE]",
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponse(streaming_lines)
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello", "--json"],
        )

        assert result.exit_code == 0
        assert "content" in result.stdout


def test_chat_send_with_rag_context(mock_config, mock_keyring):
    """Test chat with RAG file and collection context."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response with RAG context"
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
                "-p", "Search my docs",
                "--file", "file-123",
                "--collection", "coll-456",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # Verify the request was made with files context
        call_args = mock_http_client.post.call_args
        assert call_args is not None
        request_body = call_args.kwargs["json"]
        assert "files" in request_body
        assert len(request_body["files"]) == 2
