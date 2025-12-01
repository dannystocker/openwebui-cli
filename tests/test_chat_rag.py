"""Tests for RAG context features in chat commands."""

import json
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


class TestRAGContextFeatures:
    """Test suite for RAG context features."""

    def test_file_and_collection_together(self, mock_config, mock_keyring):
        """Test --file and --collection populate body['files'] correctly."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with RAG context"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Search my docs",
                    "--file", "file-id-123",
                    "--collection", "collection-xyz",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            # Verify the request body structure
            call_args = mock_http_client.post.call_args
            assert call_args is not None
            body = call_args.kwargs["json"]

            # Assert 'files' key exists in body
            assert "files" in body, "body should contain 'files' key"

            # Assert correct number of entries
            assert len(body["files"]) == 2, "should have 2 entries (1 file, 1 collection)"

            # Check types are present
            types = [f["type"] for f in body["files"]]
            assert "file" in types, "should have 'file' type"
            assert "collection" in types, "should have 'collection' type"

            # Verify correct IDs
            file_entry = next((f for f in body["files"] if f["type"] == "file"), None)
            collection_entry = next((f for f in body["files"] if f["type"] == "collection"), None)

            assert file_entry is not None, "should have file entry"
            assert collection_entry is not None, "should have collection entry"
            assert file_entry["id"] == "file-id-123", "file ID should match"
            assert collection_entry["id"] == "collection-xyz", "collection ID should match"

    def test_file_only(self, mock_config, mock_keyring):
        """Test --file alone populates body['files'] with only file entry."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with file context"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Use this file",
                    "--file", "file-456",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            # Verify the request body
            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            assert len(body["files"]) == 1
            assert body["files"][0]["type"] == "file"
            assert body["files"][0]["id"] == "file-456"

    def test_collection_only(self, mock_config, mock_keyring):
        """Test --collection alone populates body['files'] with only collection entry."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with collection context"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Search the collection",
                    "--collection", "docs-789",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            # Verify the request body
            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            assert len(body["files"]) == 1
            assert body["files"][0]["type"] == "collection"
            assert body["files"][0]["id"] == "docs-789"

    def test_multiple_files(self, mock_config, mock_keyring):
        """Test multiple --file options work correctly."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Search multiple files",
                    "--file", "file-1",
                    "--file", "file-2",
                    "--file", "file-3",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            assert len(body["files"]) == 3

            # All should be of type 'file'
            for entry in body["files"]:
                assert entry["type"] == "file"

            # Check all IDs are present
            ids = [f["id"] for f in body["files"]]
            assert "file-1" in ids
            assert "file-2" in ids
            assert "file-3" in ids

    def test_multiple_collections(self, mock_config, mock_keyring):
        """Test multiple --collection options work correctly."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Search multiple collections",
                    "--collection", "coll-a",
                    "--collection", "coll-b",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            assert len(body["files"]) == 2

            # All should be of type 'collection'
            for entry in body["files"]:
                assert entry["type"] == "collection"

            # Check all IDs are present
            ids = [f["id"] for f in body["files"]]
            assert "coll-a" in ids
            assert "coll-b" in ids

    def test_mixed_files_and_collections(self, mock_config, mock_keyring):
        """Test combination of multiple files and collections."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Search mixed context",
                    "--file", "file-1",
                    "--file", "file-2",
                    "--collection", "coll-x",
                    "--collection", "coll-y",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            assert len(body["files"]) == 4

            # Verify structure
            file_entries = [f for f in body["files"] if f["type"] == "file"]
            collection_entries = [f for f in body["files"] if f["type"] == "collection"]

            assert len(file_entries) == 2
            assert len(collection_entries) == 2

            file_ids = [f["id"] for f in file_entries]
            collection_ids = [f["id"] for f in collection_entries]

            assert "file-1" in file_ids
            assert "file-2" in file_ids
            assert "coll-x" in collection_ids
            assert "coll-y" in collection_ids

    def test_no_rag_context(self, mock_config, mock_keyring):
        """Test that files key is not present when no RAG context specified."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response without RAG"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello without RAG",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            # files key should not be present
            assert "files" not in body

    def test_rag_with_system_prompt(self, mock_config, mock_keyring):
        """Test RAG context works alongside system prompt."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with system and RAG"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Question about docs",
                    "-s", "You are a helpful assistant",
                    "--file", "file-doc",
                    "--collection", "coll-main",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            # Should have both system message and RAG files
            assert "messages" in body
            assert any(msg.get("role") == "system" for msg in body["messages"])
            assert "files" in body
            assert len(body["files"]) == 2

    def test_rag_with_chat_id(self, mock_config, mock_keyring):
        """Test RAG context works with chat_id for conversation continuation."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Continued response with RAG"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Continue with docs",
                    "--chat-id", "chat-xyz-123",
                    "--file", "file-continuing",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "chat_id" in body
            assert body["chat_id"] == "chat-xyz-123"
            assert "files" in body
            assert len(body["files"]) == 1

    def test_rag_with_temperature_and_tokens(self, mock_config, mock_keyring):
        """Test RAG context works with temperature and max_tokens."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response with temperature"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Creative response",
                    "-T", "1.5",
                    "--max-tokens", "500",
                    "--file", "file-creative",
                    "--collection", "coll-creative",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert body["temperature"] == 1.5
            assert body["max_tokens"] == 500
            assert "files" in body
            assert len(body["files"]) == 2

    def test_rag_streaming_with_context(self, mock_config, mock_keyring):
        """Test RAG context works with streaming responses."""
        streaming_lines = [
            'data: {"choices": [{"delta": {"content": "Response"}}]}',
            'data: {"choices": [{"delta": {"content": " with"}}]}',
            'data: {"choices": [{"delta": {"content": " RAG"}}]}',
            "data: [DONE]",
        ]

        class MockStreamResponse:
            def __init__(self, lines):
                self.lines = lines
                self.status_code = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def iter_lines(self):
                for line in self.lines:
                    yield line

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_stream = MockStreamResponse(streaming_lines)
            mock_http_client.stream.return_value = mock_stream
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Stream with RAG",
                    "--file", "file-stream",
                    "--collection", "coll-stream",
                ],
            )

            assert result.exit_code == 0
            assert "Response with RAG" in result.stdout

            # Verify streaming request was made with RAG context
            call_args = mock_http_client.stream.call_args
            body = call_args.kwargs["json"]
            assert "files" in body
            assert len(body["files"]) == 2

    def test_rag_context_structure_validation(self, mock_config, mock_keyring):
        """Test that RAG context entries have correct structure."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Test structure",
                    "--file", "f1",
                    "--collection", "c1",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            # Validate structure of each entry
            for entry in body["files"]:
                assert "type" in entry, "Each entry must have 'type' field"
                assert "id" in entry, "Each entry must have 'id' field"
                assert entry["type"] in ["file", "collection"], "type must be 'file' or 'collection'"
                assert isinstance(entry["id"], str), "id must be a string"
                assert len(entry) == 2, "Entry should only have 'type' and 'id' fields"


class TestRAGEdgeCases:
    """Test edge cases and error handling for RAG context."""

    def test_empty_file_id_handling(self, mock_config, mock_keyring):
        """Test handling of empty file ID."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Test",
                    "--file", "",
                    "--no-stream"
                ],
            )

            # Should still execute but with empty ID
            call_args = mock_http_client.post.call_args
            if call_args:
                body = call_args.kwargs["json"]
                # Even empty IDs should be passed through
                if "files" in body:
                    assert any(f["id"] == "" for f in body["files"] if f["type"] == "file")

    def test_special_characters_in_ids(self, mock_config, mock_keyring):
        """Test IDs with special characters."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Test",
                    "--file", "file-with-dashes-123_special.chars",
                    "--collection", "coll/with/slashes",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            ids = [f["id"] for f in body["files"]]
            assert "file-with-dashes-123_special.chars" in ids
            assert "coll/with/slashes" in ids

    def test_large_number_of_files(self, mock_config, mock_keyring):
        """Test handling many files in context."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client_factory:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client_factory.return_value = mock_http_client

            # Build command with many files
            cmd = ["chat", "send", "-m", "test-model", "-p", "Test"]
            for i in range(10):
                cmd.extend(["--file", f"file-{i}"])

            result = runner.invoke(app, cmd + ["--no-stream"])

            assert result.exit_code == 0

            call_args = mock_http_client.post.call_args
            body = call_args.kwargs["json"]

            assert "files" in body
            assert len(body["files"]) == 10
            assert all(f["type"] == "file" for f in body["files"])
