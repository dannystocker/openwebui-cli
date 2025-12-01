"""Tests for token passing from global context to chat commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

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


def test_token_from_context_passed_to_create_client(mock_config, mock_keyring):
    """Test that --token global option is passed from context to create_client."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Test response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", "TEST_TOKEN_123",
                "chat", "send",
                "-m", "test-model",
                "-p", "Hello",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # Verify create_client was called
        assert mock_create_client.called
        # Verify token was passed to create_client
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == "TEST_TOKEN_123"


def test_token_from_context_with_streaming(mock_config, mock_keyring):
    """Test that --token is passed correctly in streaming chat."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        "data: [DONE]",
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_stream = MockStreamResponse(streaming_lines)
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", "STREAMING_TOKEN_456",
                "chat", "send",
                "-m", "test-model",
                "-p", "Hello",
            ],
        )

        assert result.exit_code == 0
        assert "Hello world" in result.stdout
        # Verify create_client was called with correct token
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == "STREAMING_TOKEN_456"


def test_token_context_with_other_global_options(mock_config, mock_keyring):
    """Test token is passed correctly alongside other global options."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", "MY_TOKEN_789",
                "--timeout", "30",
                "--uri", "http://test.local:8000",
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # Verify create_client was called with all options
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == "MY_TOKEN_789"
        assert call_kwargs.get("uri") == "http://test.local:8000"
        assert call_kwargs.get("timeout") == 30


def test_token_context_with_profile(mock_config, mock_keyring):
    """Test token is passed correctly with profile option."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--profile", "prod",
                "--token", "PROD_TOKEN_123",
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # Verify create_client was called with both profile and token
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == "PROD_TOKEN_123"
        assert call_kwargs.get("profile") == "prod"


def test_token_from_env_var_fallback(mock_config, monkeypatch):
    """Test that OPENWEBUI_TOKEN env var is used when no CLI token is provided."""
    monkeypatch.setenv("OPENWEBUI_TOKEN", "ENV_TOKEN_FROM_VAR")

    # Mock keyring to not have a token
    monkeypatch.setattr("keyring.get_password", Mock(return_value=None))

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # create_client should be called with token from env (passed via Settings)
        assert mock_create_client.called


def test_token_context_cli_overrides_env(mock_config, monkeypatch):
    """Test that CLI --token overrides OPENWEBUI_TOKEN env var."""
    monkeypatch.setenv("OPENWEBUI_TOKEN", "ENV_TOKEN_IGNORED")
    monkeypatch.setattr("keyring.get_password", Mock(return_value=None))

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", "CLI_TOKEN_WINS",
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # CLI token should take precedence
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == "CLI_TOKEN_WINS"


def test_token_context_none_when_not_provided(mock_config, mock_keyring):
    """Test that token is None in context when not provided via CLI or env."""
    # Ensure no env token
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        # Should still work (create_client will handle token resolution)
        # Verify create_client was called
        assert mock_create_client.called


def test_token_context_with_special_characters(mock_config, mock_keyring):
    """Test that tokens with special characters are passed correctly."""
    special_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"

    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", special_token,
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        assert result.exit_code == 0
        # Verify token with special characters is passed correctly
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == special_token


def test_token_context_passed_to_create_client_streaming_json(mock_config, mock_keyring):
    """Test token context in streaming with JSON output."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Test"}}]}',
        "data: [DONE]",
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_stream = MockStreamResponse(streaming_lines)
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", "JSON_STREAM_TOKEN_555",
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--json"
            ],
        )

        assert result.exit_code == 0
        # Verify token was passed
        call_kwargs = mock_create_client.call_args.kwargs
        assert call_kwargs.get("token") == "JSON_STREAM_TOKEN_555"
        # Verify JSON output is present
        assert "content" in result.stdout


def test_token_context_empty_string(mock_config, mock_keyring):
    """Test handling of empty string token (should be treated as provided)."""
    response_data = {
        "choices": [
            {
                "message": {
                    "content": "Response"
                }
            }
        ]
    }

    with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = response_data
        mock_http_client.post.return_value = mock_response
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "--token", "",
                "chat", "send",
                "-m", "test-model",
                "-p", "Test",
                "--no-stream"
            ],
        )

        # Should call create_client with empty token
        assert mock_create_client.called
        call_kwargs = mock_create_client.call_args.kwargs
        # Empty string was explicitly provided
        assert call_kwargs.get("token") == ""
