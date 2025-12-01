"""Tests for chat streaming interruption (Ctrl-C handling)."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from openwebui_cli.main import app

runner = CliRunner()


class MockStreamResponseWithInterrupt:
    """Mock streaming response that raises KeyboardInterrupt during iteration."""

    def __init__(self, lines_before_interrupt=None, status_code=200):
        """Initialize with lines to yield before interrupt.

        Args:
            lines_before_interrupt: List of lines to yield before KeyboardInterrupt
            status_code: HTTP status code
        """
        self.lines_before_interrupt = lines_before_interrupt or []
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_lines(self):
        """Yield lines then raise KeyboardInterrupt."""
        for line in self.lines_before_interrupt:
            yield line
        raise KeyboardInterrupt()


class MockStreamResponseWithLateInterrupt:
    """Mock streaming response that raises KeyboardInterrupt after some output."""

    def __init__(self, lines_before_interrupt=None, status_code=200):
        """Initialize with lines to yield before interrupt.

        Args:
            lines_before_interrupt: List of lines to yield before KeyboardInterrupt
            status_code: HTTP status code
        """
        self.lines_before_interrupt = lines_before_interrupt or []
        self.status_code = status_code
        self.interrupt_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def iter_lines(self):
        """Yield lines then raise KeyboardInterrupt on second iteration."""
        for i, line in enumerate(self.lines_before_interrupt):
            yield line
            if i >= 1:  # After second line, raise interrupt
                raise KeyboardInterrupt()


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


def test_streaming_keyboard_interrupt_immediate(mock_config, mock_keyring):
    """Test KeyboardInterrupt raised immediately during streaming."""
    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=[], status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Exit code should be 0 (graceful exit)
        assert result.exit_code == 0
        # Should contain interruption message
        assert "Stream interrupted by user" in result.stdout or "Stream interrupted" in result.stdout


def test_streaming_keyboard_interrupt_after_partial_output(mock_config, mock_keyring):
    """Test KeyboardInterrupt raised after some content has been streamed."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Exit code should be 0 (graceful exit)
        assert result.exit_code == 0
        # Should have partial content output
        assert "Hello world" in result.stdout
        # Should contain interruption message
        assert "Stream interrupted by user" in result.stdout


def test_streaming_keyboard_interrupt_with_json_output(mock_config, mock_keyring):
    """Test KeyboardInterrupt with JSON output format."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Partial"}}]}',
        'data: {"choices": [{"delta": {"content": " response"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello", "--json"],
        )

        # Exit code should be 0 (graceful exit)
        assert result.exit_code == 0
        # Should contain partial content in JSON
        assert "Partial response" in result.stdout or "interrupted" in result.stdout.lower()


def test_streaming_keyboard_interrupt_message_format(mock_config, mock_keyring):
    """Test that interruption message is properly formatted."""
    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=[], status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Should exit gracefully
        assert result.exit_code == 0
        # Should have proper interruption message
        output = result.stdout.lower()
        assert "interrupt" in output or "cancel" in output


def test_streaming_keyboard_interrupt_no_crash(mock_config, mock_keyring):
    """Test that KeyboardInterrupt doesn't cause crashes or exceptions."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Test"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Should not raise exceptions (exit code 0)
        assert result.exit_code == 0
        # Should have no traceback
        assert "Traceback" not in result.stdout
        assert "Exception" not in result.stdout


def test_streaming_keyboard_interrupt_preserves_partial_content(mock_config, mock_keyring):
    """Test that partial content is preserved before interruption."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "First"}}]}',
        'data: {"choices": [{"delta": {"content": " chunk"}}]}',
        'data: {"choices": [{"delta": {"content": " of"}}]}',
        'data: {"choices": [{"delta": {"content": " text"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Should have all content streamed before interrupt
        assert "First chunk of text" in result.stdout
        # Should gracefully exit
        assert result.exit_code == 0


def test_streaming_keyboard_interrupt_with_multiple_messages(mock_config, mock_keyring):
    """Test interruption with multiple delta messages."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "A"}}]}',
        'data: {"choices": [{"delta": {"content": "B"}}]}',
        'data: {"choices": [{"delta": {"content": "C"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # All content before interrupt should be present
        assert "ABC" in result.stdout
        assert result.exit_code == 0


def test_streaming_keyboard_interrupt_with_malformed_json(mock_config, mock_keyring):
    """Test interruption with malformed JSON chunks mixed in."""
    streaming_lines = [
        'data: {"choices": [{"delta": {"content": "Valid"}}]}',
        'data: {invalid json}',  # Malformed
        'data: {"choices": [{"delta": {"content": " content"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Should handle malformed JSON gracefully and exit on interrupt
        assert result.exit_code == 0
        assert "Valid content" in result.stdout


def test_streaming_keyboard_interrupt_empty_delta(mock_config, mock_keyring):
    """Test interruption with empty delta messages."""
    streaming_lines = [
        'data: {"choices": [{"delta": {}}]}',  # Empty delta
        'data: {"choices": [{"delta": {"content": ""}}]}',  # Empty content
        'data: {"choices": [{"delta": {"content": "Real"}}]}',
    ]

    with patch("openwebui_cli.commands.chat.create_client") as mock_client:
        mock_stream = MockStreamResponseWithInterrupt(
            lines_before_interrupt=streaming_lines, status_code=200
        )
        mock_http_client = MagicMock()
        mock_http_client.__enter__.return_value = mock_http_client
        mock_http_client.__exit__.return_value = None
        mock_http_client.stream.return_value = mock_stream
        mock_client.return_value = mock_http_client

        result = runner.invoke(
            app,
            ["chat", "send", "-m", "test-model", "-p", "Hello"],
        )

        # Should skip empty deltas and get real content before interrupt
        assert "Real" in result.stdout
        assert result.exit_code == 0
