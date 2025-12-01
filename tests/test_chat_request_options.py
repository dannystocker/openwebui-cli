"""Tests for chat request body population with options."""

import json
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


def _create_mock_client(response_data=None):
    """Helper to create a mock HTTP client."""
    if response_data is None:
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    }
                }
            ]
        }

    mock_http_client = MagicMock()
    mock_http_client.__enter__.return_value = mock_http_client
    mock_http_client.__exit__.return_value = None
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data
    mock_http_client.post.return_value = mock_response

    return mock_http_client


@patch("openwebui_cli.commands.chat.create_client")
def test_chat_id_in_body(mock_create_client, mock_config, mock_keyring):
    """Test --chat-id is included in request body."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "test-model",
            "--no-stream",
            "--chat-id", "my-chat-123",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

    # Verify the request was made with chat_id in body
    call_args = mock_http_client.post.call_args
    assert call_args is not None, "post() was not called"

    body = call_args.kwargs["json"]
    assert "chat_id" in body, f"chat_id not in request body. Body: {body}"
    assert body["chat_id"] == "my-chat-123", f"Expected 'my-chat-123', got {body['chat_id']}"


@patch("openwebui_cli.commands.chat.create_client")
def test_temperature_in_body(mock_create_client, mock_config, mock_keyring):
    """Test --temperature is included in request body."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "test-model",
            "--no-stream",
            "--temperature", "0.7",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

    # Verify the request was made with temperature in body
    call_args = mock_http_client.post.call_args
    assert call_args is not None, "post() was not called"

    body = call_args.kwargs["json"]
    assert "temperature" in body, f"temperature not in request body. Body: {body}"
    assert body["temperature"] == 0.7, f"Expected 0.7, got {body['temperature']}"


@patch("openwebui_cli.commands.chat.create_client")
def test_max_tokens_in_body(mock_create_client, mock_config, mock_keyring):
    """Test --max-tokens is included in request body."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "test-model",
            "--no-stream",
            "--max-tokens", "1000",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

    # Verify the request was made with max_tokens in body
    call_args = mock_http_client.post.call_args
    assert call_args is not None, "post() was not called"

    body = call_args.kwargs["json"]
    assert "max_tokens" in body, f"max_tokens not in request body. Body: {body}"
    assert body["max_tokens"] == 1000, f"Expected 1000, got {body['max_tokens']}"


@patch("openwebui_cli.commands.chat.create_client")
def test_all_options_combined(mock_create_client, mock_config, mock_keyring):
    """Test all request body options together."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "test-model",
            "--no-stream",
            "--chat-id", "combined-chat-456",
            "--temperature", "0.5",
            "--max-tokens", "2000",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

    # Verify all options are in the request body
    call_args = mock_http_client.post.call_args
    assert call_args is not None, "post() was not called"

    body = call_args.kwargs["json"]

    # Verify chat_id
    assert "chat_id" in body, f"chat_id not in request body. Body: {body}"
    assert body["chat_id"] == "combined-chat-456"

    # Verify temperature
    assert "temperature" in body, f"temperature not in request body. Body: {body}"
    assert body["temperature"] == 0.5

    # Verify max_tokens
    assert "max_tokens" in body, f"max_tokens not in request body. Body: {body}"
    assert body["max_tokens"] == 2000

    # Verify core fields are still present
    assert "model" in body
    assert body["model"] == "test-model"
    assert "messages" in body
    assert "stream" in body


@patch("openwebui_cli.commands.chat.create_client")
def test_temperature_with_different_values(mock_create_client, mock_config, mock_keyring):
    """Test temperature with various valid values."""
    test_values = [0.0, 0.3, 1.0, 1.5, 2.0]

    for temp_value in test_values:
        mock_http_client = _create_mock_client()
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "--model", "test-model",
                "--no-stream",
                "--temperature", str(temp_value),
                "--prompt", "Hello"
            ],
        )

        assert result.exit_code == 0, f"Command failed for temperature {temp_value}"

        call_args = mock_http_client.post.call_args
        body = call_args.kwargs["json"]
        assert body["temperature"] == temp_value, f"Temperature mismatch for {temp_value}"


@patch("openwebui_cli.commands.chat.create_client")
def test_max_tokens_with_different_values(mock_create_client, mock_config, mock_keyring):
    """Test max-tokens with various values."""
    test_values = [100, 500, 1000, 4000, 8000]

    for token_value in test_values:
        mock_http_client = _create_mock_client()
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "--model", "test-model",
                "--no-stream",
                "--max-tokens", str(token_value),
                "--prompt", "Hello"
            ],
        )

        assert result.exit_code == 0, f"Command failed for max-tokens {token_value}"

        call_args = mock_http_client.post.call_args
        body = call_args.kwargs["json"]
        assert body["max_tokens"] == token_value, f"Max tokens mismatch for {token_value}"


@patch("openwebui_cli.commands.chat.create_client")
def test_options_not_in_body_when_not_provided(mock_create_client, mock_config, mock_keyring):
    """Test that optional fields are not in body when not provided."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "test-model",
            "--no-stream",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0

    call_args = mock_http_client.post.call_args
    body = call_args.kwargs["json"]

    # These should not be in the body when not provided
    assert "chat_id" not in body, "chat_id should not be in body when not provided"
    assert "temperature" not in body, "temperature should not be in body when not provided"
    assert "max_tokens" not in body, "max_tokens should not be in body when not provided"


@patch("openwebui_cli.commands.chat.create_client")
def test_chat_id_with_special_characters(mock_create_client, mock_config, mock_keyring):
    """Test chat-id with special characters and UUID-like format."""
    special_ids = [
        "uuid-12345-67890-abcdef",
        "chat_2025_01_01_001",
        "conversation-abc123xyz",
    ]

    for chat_id_value in special_ids:
        mock_http_client = _create_mock_client()
        mock_create_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            [
                "chat", "send",
                "--model", "test-model",
                "--no-stream",
                "--chat-id", chat_id_value,
                "--prompt", "Hello"
            ],
        )

        assert result.exit_code == 0, f"Command failed for chat_id {chat_id_value}"

        call_args = mock_http_client.post.call_args
        body = call_args.kwargs["json"]
        assert body["chat_id"] == chat_id_value, f"Chat ID mismatch for {chat_id_value}"


@patch("openwebui_cli.commands.chat.create_client")
def test_request_body_has_core_fields(mock_create_client, mock_config, mock_keyring):
    """Test that core request fields are always present."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "test-model",
            "--no-stream",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0

    call_args = mock_http_client.post.call_args
    body = call_args.kwargs["json"]

    # Core fields that should always be present
    assert "model" in body, "model must be in request body"
    assert body["model"] == "test-model"
    assert "messages" in body, "messages must be in request body"
    assert isinstance(body["messages"], list), "messages must be a list"
    assert "stream" in body, "stream must be in request body"


@patch("openwebui_cli.commands.chat.create_client")
def test_all_options_with_system_prompt(mock_create_client, mock_config, mock_keyring):
    """Test request options with system prompt included."""
    mock_http_client = _create_mock_client()
    mock_create_client.return_value = mock_http_client

    result = runner.invoke(
        app,
        [
            "chat", "send",
            "--model", "gpt-4",
            "--no-stream",
            "--system", "You are a helpful assistant",
            "--chat-id", "sys-chat-789",
            "--temperature", "0.8",
            "--max-tokens", "3000",
            "--prompt", "Hello"
        ],
    )

    assert result.exit_code == 0

    call_args = mock_http_client.post.call_args
    body = call_args.kwargs["json"]

    # Check all options
    assert body["model"] == "gpt-4"
    assert body["chat_id"] == "sys-chat-789"
    assert body["temperature"] == 0.8
    assert body["max_tokens"] == 3000

    # Check system prompt is in messages
    assert len(body["messages"]) >= 2
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][0]["content"] == "You are a helpful assistant"
