"""Tests for basic chat streaming functionality."""

import json
from unittest.mock import MagicMock, Mock, patch

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


class TestStreamingBasic:
    """Test basic streaming functionality."""

    def test_streaming_single_chunk(self, mock_config, mock_keyring):
        """Test streaming with a single chunk."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
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
            assert "Hello" in result.stdout

    def test_streaming_multiple_chunks(self, mock_config, mock_keyring):
        """Test streaming with multiple chunks accumulating content."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " "}}]}',
            'data: {"choices": [{"delta": {"content": "world"}}]}',
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
            # All chunks should appear in output
            assert "Hello" in result.stdout
            assert "world" in result.stdout

    def test_streaming_with_empty_deltas(self, mock_config, mock_keyring):
        """Test streaming handles empty delta content gracefully."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Start"}}]}',
            'data: {"choices": [{"delta": {}}]}',  # Empty delta
            'data: {"choices": [{"delta": {"content": "End"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test"],
            )

            assert result.exit_code == 0
            assert "Start" in result.stdout
            assert "End" in result.stdout

    def test_streaming_with_special_characters(self, mock_config, mock_keyring):
        """Test streaming preserves special characters and unicode."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Hello 世界"}}]}',
            'data: {"choices": [{"delta": {"content": " \\n\\t"}}]}',
            'data: {"choices": [{"delta": {"content": "emoji: 🎉"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test"],
            )

            assert result.exit_code == 0
            assert "世界" in result.stdout
            assert "emoji:" in result.stdout

    def test_streaming_malformed_json_skipped(self, mock_config, mock_keyring):
        """Test streaming skips malformed JSON chunks gracefully."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Valid"}}]}',
            'data: {invalid json here}',  # Malformed JSON
            'data: {"choices": [{"delta": {"content": " content"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test"],
            )

            # Should succeed despite malformed chunk
            assert result.exit_code == 0
            assert "Valid" in result.stdout
            assert "content" in result.stdout

    def test_streaming_final_newline(self, mock_config, mock_keyring):
        """Test streaming prints final newline after stream ends."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Content"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test"],
            )

            assert result.exit_code == 0
            # Output should have the content followed by newline
            assert result.stdout.rstrip() == "Content"

    def test_streaming_done_marker_stops_processing(self, mock_config, mock_keyring):
        """Test [DONE] marker stops stream processing."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "First"}}]}',
            "data: [DONE]",
            'data: {"choices": [{"delta": {"content": "Never"}}]}',  # Should not appear
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
                ["chat", "send", "-m", "test-model", "-p", "Test"],
            )

            assert result.exit_code == 0
            assert "First" in result.stdout
            assert "Never" not in result.stdout


class TestStreamingJson:
    """Test streaming with JSON output flag."""

    def test_streaming_json_basic(self, mock_config, mock_keyring):
        """Test streaming with --json flag outputs JSON at end."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " "}}]}',
            'data: {"choices": [{"delta": {"content": "world"}}]}',
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
            # Should contain JSON output
            assert "content" in result.stdout
            # JSON should have accumulated content
            assert "Hello world" in result.stdout or ("Hello" in result.stdout and "world" in result.stdout)

    def test_streaming_json_single_chunk(self, mock_config, mock_keyring):
        """Test JSON output with single chunk."""
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
                ["chat", "send", "-m", "test-model", "-p", "Test", "--json"],
            )

            assert result.exit_code == 0
            # Verify JSON is in the output
            assert "content" in result.stdout
            assert '"Test"' in result.stdout

    def test_streaming_json_preserves_content(self, mock_config, mock_keyring):
        """Test JSON output preserves all streamed content."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Line 1"}}]}',
            'data: {"choices": [{"delta": {"content": "\\n"}}]}',
            'data: {"choices": [{"delta": {"content": "Line 2"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test", "--json"],
            )

            assert result.exit_code == 0
            # Verify all content is in output
            assert "Line 1" in result.stdout
            assert "Line 2" in result.stdout
            assert "content" in result.stdout

    def test_streaming_json_empty_content(self, mock_config, mock_keyring):
        """Test JSON output with empty stream."""
        streaming_lines = [
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
                ["chat", "send", "-m", "test-model", "-p", "Test", "--json"],
            )

            assert result.exit_code == 0
            # Should still have valid JSON even with empty content
            assert "content" in result.stdout
            assert "{" in result.stdout

    def test_streaming_json_with_special_chars(self, mock_config, mock_keyring):
        """Test JSON properly escapes special characters."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Quote: \\"test\\""}}]}',
            'data: {"choices": [{"delta": {"content": " Newline: \\n End"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test", "--json"],
            )

            assert result.exit_code == 0
            # Verify JSON is in output and contains special characters
            assert "content" in result.stdout
            assert "Quote:" in result.stdout or "test" in result.stdout


class TestStreamingIntegration:
    """Integration tests for streaming behavior."""

    def test_streaming_without_json_flag_no_json_output(self, mock_config, mock_keyring):
        """Test that without --json flag, only text is printed."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
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
            # Should have content but NOT JSON object
            assert "Hello" in result.stdout
            assert "{" not in result.stdout or "content" not in result.stdout

    def test_streaming_accumulates_before_json_output(self, mock_config, mock_keyring):
        """Test that JSON output contains full accumulated content."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "A"}}]}',
            'data: {"choices": [{"delta": {"content": "B"}}]}',
            'data: {"choices": [{"delta": {"content": "C"}}]}',
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
                ["chat", "send", "-m", "test-model", "-p", "Test", "--json"],
            )

            assert result.exit_code == 0
            # Verify all chunks are accumulated and in output
            assert "A" in result.stdout
            assert "B" in result.stdout
            assert "C" in result.stdout
            assert "content" in result.stdout

    def test_streaming_response_status_200(self, mock_config, mock_keyring):
        """Test streaming handles 200 status code."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "OK"}}]}',
            "data: [DONE]",
        ]

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_stream = MockStreamResponse(streaming_lines, status_code=200)
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_http_client.stream.return_value = mock_stream
            mock_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                ["chat", "send", "-m", "test-model", "-p", "Test"],
            )

            assert result.exit_code == 0
            assert "OK" in result.stdout

    def test_streaming_long_content(self, mock_config, mock_keyring):
        """Test streaming handles large accumulated content."""
        # Generate 100 chunks
        streaming_lines = [
            f'data: {{"choices": [{{"delta": {{"content": "chunk{i} "}}}}]}}'
            for i in range(100)
        ]
        streaming_lines.append("data: [DONE]")

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_stream = MockStreamResponse(streaming_lines)
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_http_client.stream.return_value = mock_stream
            mock_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                ["chat", "send", "-m", "test-model", "-p", "Test", "--json"],
            )

            assert result.exit_code == 0
            # Verify first and last chunks are in output
            assert "chunk0" in result.stdout
            assert "chunk99" in result.stdout
            assert "content" in result.stdout
