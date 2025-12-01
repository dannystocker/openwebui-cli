"""Tests for non-streaming chat modes."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
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


class TestNonStreamingJSON:
    """Tests for non-streaming mode with --json output."""

    def test_nonstream_with_json_flag(self, mock_config, mock_keyring):
        """Test non-streaming response with --json flag."""
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Complete response from model"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream", "--json"],
            )

            assert result.exit_code == 0
            # Verify JSON output is printed
            output = json.loads(result.stdout)
            assert "choices" in output
            assert output["choices"][0]["message"]["content"] == "Complete response from model"

    def test_nonstream_json_with_multiple_fields(self, mock_config, mock_keyring):
        """Test that --json outputs complete response object."""
        response_data = {
            "id": "test-id-456",
            "model": "gpt-4",
            "choices": [
                {
                    "message": {
                        "content": "Detailed response with metadata"
                    },
                    "finish_reason": "length"
                }
            ],
            "usage": {
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150
            }
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
                ["chat", "send", "-m", "gpt-4", "-p", "Test", "--no-stream", "--json"],
            )

            assert result.exit_code == 0
            output = json.loads(result.stdout)
            assert output["id"] == "test-id-456"
            assert output["usage"]["total_tokens"] == 150
            assert output["choices"][0]["finish_reason"] == "length"

    def test_nonstream_json_preserves_full_response(self, mock_config, mock_keyring):
        """Test that complete API response is returned with --json."""
        response_data = {
            "custom_field": "should_be_included",
            "model": "test-model",
            "choices": [
                {
                    "message": {
                        "content": "Response content"
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
                ["chat", "send", "-m", "test-model", "-p", "Test", "--no-stream", "--json"],
            )

            assert result.exit_code == 0
            output = json.loads(result.stdout)
            assert output["custom_field"] == "should_be_included"


class TestNonStreamingPlainText:
    """Tests for non-streaming mode without --json (plain text output)."""

    def test_nonstream_plain_text_output(self, mock_config, mock_keyring):
        """Test non-streaming response outputs plain text content."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "This is the plain text response"
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
            )

            assert result.exit_code == 0
            # Without --json, only the content text should be printed
            assert "This is the plain text response" in result.stdout
            # Should NOT contain JSON structure
            assert "{" not in result.stdout or result.stdout.count("{") == 0

    def test_nonstream_plain_text_extracts_content_only(self, mock_config, mock_keyring):
        """Test that plain text mode extracts only message content."""
        response_data = {
            "id": "chatcmpl-789",
            "model": "gpt-3.5",
            "created": 1234567890,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Just the content without metadata"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 30,
                "total_tokens": 50
            }
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
                ["chat", "send", "-m", "gpt-3.5", "-p", "Test", "--no-stream"],
            )

            assert result.exit_code == 0
            # Only the content should appear
            assert "Just the content without metadata" in result.stdout
            # Metadata should NOT appear
            assert "chatcmpl-789" not in result.stdout
            assert "finish_reason" not in result.stdout

    def test_nonstream_plain_text_multiline_response(self, mock_config, mock_keyring):
        """Test plain text output with multiline content."""
        multiline_content = """This is a multiline response.
It contains multiple lines.
And some code:

```python
def hello():
    print("world")
```

More text here."""

        response_data = {
            "choices": [
                {
                    "message": {
                        "content": multiline_content
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
                ["chat", "send", "-m", "test-model", "-p", "Code request", "--no-stream"],
            )

            assert result.exit_code == 0
            assert "multiline response" in result.stdout
            assert "def hello():" in result.stdout
            assert 'print("world")' in result.stdout


class TestNonStreamingEdgeCases:
    """Tests for non-streaming mode edge cases."""

    def test_nonstream_empty_content(self, mock_config, mock_keyring):
        """Test non-streaming response with empty content."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": ""
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
            )

            assert result.exit_code == 0

    def test_nonstream_missing_content_field(self, mock_config, mock_keyring):
        """Test non-streaming with missing content field."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "role": "assistant"
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
            )

            assert result.exit_code == 0

    def test_nonstream_special_characters_json(self, mock_config, mock_keyring):
        """Test non-streaming JSON output with special characters."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with special chars: é, ñ, 中文"
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream", "--json"],
            )

            assert result.exit_code == 0
            output = json.loads(result.stdout)
            assert "é" in output["choices"][0]["message"]["content"]
            assert "中文" in output["choices"][0]["message"]["content"]

    def test_nonstream_json_with_newlines_in_content(self, mock_config, mock_keyring):
        """Test JSON output correctly handles newlines in content."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Line 1\nLine 2\nLine 3"
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream", "--json"],
            )

            assert result.exit_code == 0
            output = json.loads(result.stdout)
            content = output["choices"][0]["message"]["content"]
            assert "Line 1" in content
            assert "Line 2" in content
            assert "Line 3" in content


class TestNonStreamingWithOptions:
    """Tests for non-streaming mode with various command options."""

    def test_nonstream_with_system_prompt(self, mock_config, mock_keyring):
        """Test non-streaming with system prompt."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response respecting system prompt"
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
                    "-p", "Hello",
                    "-s", "You are a helpful assistant",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify system prompt was included in request
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            messages = request_body["messages"]
            assert any(msg.get("role") == "system" for msg in messages)

    def test_nonstream_with_temperature(self, mock_config, mock_keyring):
        """Test non-streaming with temperature parameter."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Creative response"
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
                    "-p", "Be creative",
                    "-T", "1.5",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify temperature was included in request
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            assert request_body["temperature"] == 1.5

    def test_nonstream_with_max_tokens(self, mock_config, mock_keyring):
        """Test non-streaming with max-tokens parameter."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Limited response"
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
                    "-p", "Be brief",
                    "--max-tokens", "50",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify max_tokens was included in request
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            assert request_body["max_tokens"] == 50

    def test_nonstream_with_chat_id(self, mock_config, mock_keyring):
        """Test non-streaming continuing an existing conversation."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Continuation response"
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
                    "-p", "Continue",
                    "--chat-id", "chat-abc-123",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify chat_id was included in request
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            assert request_body["chat_id"] == "chat-abc-123"

    def test_nonstream_with_rag_context(self, mock_config, mock_keyring):
        """Test non-streaming with RAG file and collection context."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response using RAG context"
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
                    "-p", "Search my docs",
                    "--file", "file-123",
                    "--collection", "coll-456",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify files context was included
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            assert "files" in request_body
            assert len(request_body["files"]) == 2

    def test_nonstream_post_method_called(self, mock_config, mock_keyring):
        """Test that POST method is used for non-streaming (not stream)."""
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
            )

            assert result.exit_code == 0
            # Verify post was called, not stream
            mock_http_client.post.assert_called_once()
            mock_http_client.stream.assert_not_called()

    def test_nonstream_correct_endpoint(self, mock_config, mock_keyring):
        """Test that correct API endpoint is called."""
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
            )

            assert result.exit_code == 0
            # Verify correct endpoint
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            assert call_args[0][0] == "/api/v1/chat/completions"


class TestNonStreamingWithHistory:
    """Tests for non-streaming mode with conversation history."""

    def test_nonstream_with_history_file(self, tmp_path, mock_config, mock_keyring):
        """Test non-streaming with conversation history file."""
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
                    "-p", "What about 3+3?",
                    "--history-file", str(history_file),
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify history was included in request
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            messages = request_body["messages"]
            assert len(messages) == 3  # 2 from history + 1 new user message

    def test_nonstream_with_history_and_system_prompt(self, tmp_path, mock_config, mock_keyring):
        """Test non-streaming with history file and system prompt."""
        history_file = tmp_path / "history.json"
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ]
        with open(history_file, "w") as f:
            json.dump(history, f)

        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with both history and system prompt"
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
                    "-p", "Second question",
                    "-s", "You are a helpful assistant",
                    "--history-file", str(history_file),
                    "--no-stream",
                    "--json"
                ],
            )

            assert result.exit_code == 0
            output = json.loads(result.stdout)
            assert output["choices"][0]["message"]["content"]


class TestNonStreamingErrorHandling:
    """Tests for non-streaming mode error handling."""

    def test_nonstream_with_stdin(self, mock_config, mock_keyring):
        """Test non-streaming with stdin input."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response from stdin"
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
                ["chat", "send", "-m", "test-model", "--no-stream"],
                input="Hello from stdin\n",
            )

            assert result.exit_code == 0

    def test_nonstream_request_body_structure(self, mock_config, mock_keyring):
        """Test that request body has correct structure."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Test"
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
                ["chat", "send", "-m", "test-model", "-p", "Hello", "--no-stream"],
            )

            assert result.exit_code == 0
            # Verify request structure
            call_args = mock_http_client.post.call_args
            request_body = call_args.kwargs["json"]
            assert "model" in request_body
            assert "messages" in request_body
            assert "stream" in request_body
            assert request_body["stream"] is False
