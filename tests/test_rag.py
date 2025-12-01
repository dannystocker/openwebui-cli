"""Tests for RAG commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from openwebui_cli.errors import ServerError
from openwebui_cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_config(tmp_path, monkeypatch):
    """Isolate config writes."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"
    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    from openwebui_cli.config import Config, save_config

    save_config(Config())
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


def _mock_client(get_data=None, post_data=None, delete_data=None, status_code=200):
    """Helper to create mock HTTP client."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = None

    if get_data is not None:
        get_response = Mock()
        get_response.status_code = status_code
        get_response.json.return_value = get_data
        client.get.return_value = get_response

    if post_data is not None:
        post_response = Mock()
        post_response.status_code = status_code
        post_response.json.return_value = post_data
        client.post.return_value = post_response

    if delete_data is not None:
        delete_response = Mock()
        delete_response.status_code = status_code
        delete_response.json.return_value = delete_data
        client.delete.return_value = delete_response

    return client


# ===== Files Commands =====

def test_files_list_success(mock_keyring):
    """Test listing files successfully."""
    files = [
        {"id": "file-1", "filename": "doc.pdf", "size": 2048},
        {"id": "file-2", "name": "report.txt", "size": 1024},
    ]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=files)

        result = runner.invoke(app, ["rag", "files", "list"])

        assert result.exit_code == 0
        assert "doc.pdf" in result.stdout
        assert "report.txt" in result.stdout
        assert "2.0 KB" in result.stdout
        assert "1.0 KB" in result.stdout


def test_files_list_empty(mock_keyring):
    """Test listing files when none exist."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=[])

        result = runner.invoke(app, ["rag", "files", "list"])

        assert result.exit_code == 0
        assert "No files found" in result.stdout


def test_files_list_json_format(mock_keyring):
    """Test listing files in JSON format."""
    files = [{"id": "file-1", "filename": "doc.pdf", "size": 2048}]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=files)

        result = runner.invoke(app, ["--format", "json", "rag", "files", "list"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert isinstance(output, list)
        assert output[0]["id"] == "file-1"


def test_files_list_wrapped_response(mock_keyring):
    """Test listing files when API wraps response in object."""
    response = {"files": [{"id": "file-1", "filename": "doc.pdf", "size": 2048}]}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=response)

        result = runner.invoke(app, ["rag", "files", "list"])

        assert result.exit_code == 0
        assert "doc.pdf" in result.stdout


def test_files_upload_success(tmp_path, mock_keyring):
    """Test uploading a file successfully."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")

    response = {"id": "file-123", "filename": "test.pdf"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(app, ["rag", "files", "upload", str(test_file)])

        assert result.exit_code == 0
        assert "Uploaded: test.pdf" in result.stdout
        assert "file-123" in result.stdout
        # Verify the client was created with extended timeout
        mock_client_factory.assert_called_once()
        call_kwargs = mock_client_factory.call_args.kwargs
        assert call_kwargs.get("timeout") == 300


def test_files_upload_missing_file(mock_keyring):
    """Test uploading a non-existent file."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_factory.return_value = mock_client

        result = runner.invoke(app, ["rag", "files", "upload", "/nonexistent/file.pdf"])

        assert result.exit_code == 0
        assert "Error: File not found: /nonexistent/file.pdf" in result.stdout
        assert "Summary: 0 successful, 1 failed" in result.stdout


def test_files_upload_multiple_files(tmp_path, mock_keyring):
    """Test uploading multiple files."""
    file1 = tmp_path / "doc1.pdf"
    file2 = tmp_path / "doc2.pdf"
    file1.write_text("content1")
    file2.write_text("content2")

    response1 = {"id": "file-1", "filename": "doc1.pdf"}
    response2 = {"id": "file-2", "filename": "doc2.pdf"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        # Mock multiple post responses
        mock_client.post.side_effect = [
            Mock(status_code=200, json=lambda: response1),
            Mock(status_code=200, json=lambda: response2),
        ]
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "files", "upload", str(file1), str(file2)]
        )

        assert result.exit_code == 0
        assert "Uploaded: doc1.pdf" in result.stdout
        assert "Uploaded: doc2.pdf" in result.stdout
        assert mock_client.post.call_count == 2


def test_files_upload_with_collection(tmp_path, mock_keyring):
    """Test uploading a file and adding to collection."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")

    upload_response = {"id": "file-123", "filename": "test.pdf"}
    add_response = {}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        # First post for upload, second post for adding to collection
        mock_client.post.side_effect = [
            Mock(status_code=200, json=lambda: upload_response),
            Mock(status_code=200, json=lambda: add_response),
        ]
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "files", "upload", str(test_file), "--collection", "coll-456"],
        )

        assert result.exit_code == 0
        assert "Uploaded: test.pdf" in result.stdout
        assert "Added to collection: coll-456" in result.stdout
        # Verify both API calls were made
        assert mock_client.post.call_count == 2


def test_files_upload_collection_failure_continues(tmp_path, mock_keyring):
    """Test that collection add failure doesn't block upload."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")

    upload_response = {"id": "file-123", "filename": "test.pdf"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        # First post succeeds, second raises exception
        mock_client.post.side_effect = [
            Mock(status_code=200, json=lambda: upload_response),
            Exception("Collection not found"),
        ]
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "files", "upload", str(test_file), "--collection", "invalid"],
        )

        assert result.exit_code == 0
        assert "Uploaded: test.pdf" in result.stdout
        assert "Error: Could not add to collection" in result.stdout
        assert "Summary: 1 successful, 0 failed" in result.stdout


def test_files_upload_unknown_id(tmp_path, mock_keyring):
    """Test uploading when response has no ID."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")

    response = {"filename": "test.pdf"}  # No ID

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(app, ["rag", "files", "upload", str(test_file)])

        assert result.exit_code == 0
        assert "Warning: Upload succeeded but got no file ID" in result.stdout
        assert "Summary: 0 successful, 1 failed" in result.stdout


def test_files_delete_with_confirmation(mock_keyring):
    """Test deleting a file with user confirmation."""
    response = {}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(delete_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "files", "delete", "file-123"], input="y\n"
        )

        assert result.exit_code == 0
        assert "Deleted file: file-123" in result.stdout
        mock_client.delete.assert_called_once_with("/api/v1/files/file-123")


def test_files_delete_skip_confirmation(mock_keyring):
    """Test deleting a file with force flag."""
    response = {}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(delete_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "files", "delete", "file-123", "--force"]
        )

        assert result.exit_code == 0
        assert "Deleted file: file-123" in result.stdout


def test_files_delete_abort(mock_keyring):
    """Test aborting file deletion."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "files", "delete", "file-123"], input="n\n"
        )

        assert result.exit_code == 1  # Abort returns exit code 1


# ===== Collections Commands =====

def test_collections_list_success(mock_keyring):
    """Test listing collections successfully."""
    collections = [
        {"id": "coll-1", "name": "Documents", "description": "All documents"},
        {"id": "coll-2", "name": "Articles", "description": "Research articles"},
    ]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=collections)

        result = runner.invoke(app, ["rag", "collections", "list"])

        assert result.exit_code == 0
        assert "Documents" in result.stdout
        assert "Articles" in result.stdout
        assert "All documents" in result.stdout


def test_collections_list_empty(mock_keyring):
    """Test listing collections when none exist."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=[])

        result = runner.invoke(app, ["rag", "collections", "list"])

        assert result.exit_code == 0
        assert "No collections found" in result.stdout


def test_collections_list_json_format(mock_keyring):
    """Test listing collections in JSON format."""
    collections = [
        {"id": "coll-1", "name": "Documents", "description": "All documents"}
    ]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=collections)

        result = runner.invoke(app, ["--format", "json", "rag", "collections", "list"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert isinstance(output, list)
        assert output[0]["name"] == "Documents"


def test_collections_list_wrapped_response(mock_keyring):
    """Test listing collections when API wraps response in object."""
    response = {
        "collections": [{"id": "coll-1", "name": "Documents", "description": "Test"}]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=response)

        result = runner.invoke(app, ["rag", "collections", "list"])

        assert result.exit_code == 0
        assert "Documents" in result.stdout


def test_collections_list_truncated_description(mock_keyring):
    """Test that long descriptions are truncated."""
    collections = [
        {
            "id": "coll-1",
            "name": "Docs",
            "description": "A" * 100,  # Very long description
        }
    ]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=collections)

        result = runner.invoke(app, ["rag", "collections", "list"])

        assert result.exit_code == 0
        # Description should be truncated to 50 chars
        assert "A" * 50 in result.stdout or result.stdout.count("A") <= 50


def test_collections_create_success(mock_keyring):
    """Test creating a collection successfully."""
    response = {"id": "coll-789", "name": "New Collection"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "collections", "create", "New Collection"],
        )

        assert result.exit_code == 0
        assert "Created collection: New Collection" in result.stdout
        assert "coll-789" in result.stdout

        # Verify the request was made correctly
        mock_client.post.assert_called_once_with(
            "/api/v1/knowledge/",
            json={"name": "New Collection", "description": ""},
        )


def test_collections_create_with_description(mock_keyring):
    """Test creating a collection with description."""
    response = {"id": "coll-789", "name": "New Collection"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "rag",
                "collections",
                "create",
                "New Collection",
                "--description",
                "Test description",
            ],
        )

        assert result.exit_code == 0
        assert "Created collection: New Collection" in result.stdout

        # Verify the request includes description
        mock_client.post.assert_called_once_with(
            "/api/v1/knowledge/",
            json={"name": "New Collection", "description": "Test description"},
        )


def test_collections_create_no_id_response(mock_keyring):
    """Test creating collection when response has no ID."""
    response = {"name": "New Collection"}  # No ID

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "collections", "create", "New Collection"],
        )

        assert result.exit_code == 0
        assert "Warning: Collection created but got no ID" in result.stdout


def test_collections_delete_with_confirmation(mock_keyring):
    """Test deleting a collection with user confirmation."""
    response = {}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(delete_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "collections", "delete", "coll-456"], input="y\n"
        )

        assert result.exit_code == 0
        assert "Deleted collection: coll-456" in result.stdout
        mock_client.delete.assert_called_once_with("/api/v1/knowledge/coll-456")


def test_collections_delete_skip_confirmation(mock_keyring):
    """Test deleting a collection with force flag."""
    response = {}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(delete_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "collections", "delete", "coll-456", "--force"],
        )

        assert result.exit_code == 0
        assert "Deleted collection: coll-456" in result.stdout


def test_collections_delete_abort(mock_keyring):
    """Test aborting collection deletion."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "collections", "delete", "coll-456"], input="n\n"
        )

        assert result.exit_code == 0  # Returns normally with cancellation message
        assert "Delete cancelled" in result.stdout


# ===== Search Command =====

def test_search_success(mock_keyring):
    """Test searching in a collection successfully."""
    results = {
        "results": [
            {"content": "Hello world", "score": 0.95},
            {"content": "Hello there", "score": 0.87},
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "hello", "--collection", "coll-1", "--top-k", "2"],
        )

        assert result.exit_code == 0
        assert "Search results for: hello" in result.stdout
        assert "Hello world" in result.stdout
        assert "Hello there" in result.stdout
        assert "0.95" in result.stdout

        # Verify the request
        mock_client.post.assert_called_once_with(
            "/api/v1/knowledge/coll-1/query",
            json={"query": "hello", "k": 2},
        )


def test_search_default_top_k(mock_keyring):
    """Test search with default top_k value."""
    results = {"results": [{"content": "Result", "score": 0.9}]}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1"],
        )

        assert result.exit_code == 0

        # Verify default k=5 was used
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["k"] == 5


def test_search_no_results(mock_keyring):
    """Test search with no results."""
    results = {"results": []}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "nosuchterm", "--collection", "coll-1"],
        )

        assert result.exit_code == 0
        assert "No results found for query" in result.stdout


def test_search_documents_fallback(mock_keyring):
    """Test search when response uses 'documents' key instead of 'results'."""
    results = {
        "documents": [
            {"text": "Document content", "distance": 0.05},
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1"],
        )

        assert result.exit_code == 0
        assert "Document content" in result.stdout


def test_search_json_format(mock_keyring):
    """Test search with JSON output format."""
    results = {
        "results": [
            {"content": "Test result", "score": 0.92},
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            [
                "--format",
                "json",
                "rag",
                "search",
                "query",
                "--collection",
                "coll-1",
            ],
        )

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert isinstance(output, list)
        assert output[0]["content"] == "Test result"


def test_search_long_content_truncated(mock_keyring):
    """Test that long search result content is truncated."""
    long_text = "A" * 500
    results = {
        "results": [
            {"content": long_text, "score": 0.9},
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1"],
        )

        assert result.exit_code == 0
        # Content should be truncated to 200 chars
        assert result.stdout.count("A") <= 200


def test_search_with_short_option(mock_keyring):
    """Test search using short option flags."""
    results = {"results": [{"content": "Result", "score": 0.9}]}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "-c", "coll-1", "-k", "3"],
        )

        assert result.exit_code == 0
        call_args = mock_client.post.call_args
        assert call_args.kwargs["json"]["k"] == 3


# ===== Error Handling =====

def test_files_list_api_error(mock_keyring):
    """Test handling API error when listing files."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.get.side_effect = ServerError("API error")
        mock_client_factory.return_value = mock_client

        result = runner.invoke(app, ["rag", "files", "list"])

        # Should handle error gracefully
        assert result.exit_code != 0


def test_collections_create_api_error(mock_keyring):
    """Test handling API error when creating collection."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.side_effect = ServerError("API error")
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "collections", "create", "Test"]
        )

        # Should handle error gracefully
        assert result.exit_code != 0


def test_search_api_error(mock_keyring):
    """Test handling API error when searching."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client.post.side_effect = ServerError("Collection not found")
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "invalid"],
        )

        # Should handle error gracefully
        assert result.exit_code != 0


# ===== Edge Cases =====

def test_files_list_missing_fields(mock_keyring):
    """Test listing files when response has missing fields."""
    files = [
        {"id": "file-1"},  # Missing filename and size
        {"filename": "doc.pdf"},  # Missing id and size
    ]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=files)

        result = runner.invoke(app, ["rag", "files", "list"])

        assert result.exit_code == 0
        assert "-" in result.stdout  # Missing fields should show as "-"


def test_collections_list_missing_fields(mock_keyring):
    """Test listing collections when response has missing fields."""
    collections = [
        {"id": "coll-1"},  # Missing name and description
        {"name": "Docs"},  # Missing id and description
    ]

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(get_data=collections)

        result = runner.invoke(app, ["rag", "collections", "list"])

        assert result.exit_code == 0
        assert "-" in result.stdout  # Missing fields should show as "-"


def test_search_with_metadata(mock_keyring):
    """Test search results with metadata information."""
    results = {
        "results": [
            {
                "content": "Result with metadata",
                "score": 0.95,
                "metadata": {"source": "test.pdf"},
            }
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1"],
        )

        assert result.exit_code == 0
        assert "Result with metadata" in result.stdout
        assert "Source: test.pdf" in result.stdout


def test_files_upload_with_missing_collection_id(tmp_path, mock_keyring):
    """Test that upload continues even if file ID is missing."""
    test_file = tmp_path / "test.pdf"
    test_file.write_text("test content")

    # API returns no ID
    upload_response = {"filename": "test.pdf"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=upload_response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "files", "upload", str(test_file), "--collection", "coll-456"],
        )

        assert result.exit_code == 0
        assert "Warning: Upload succeeded but got no file ID" in result.stdout
        # Collection add should be skipped since file_id == "unknown"
        assert mock_client.post.call_count == 1  # Only upload attempt, no collection add
        assert "Summary: 0 successful, 1 failed" in result.stdout


# ===== Additional Coverage Tests =====

def test_files_upload_large_file_warning(tmp_path, mock_keyring):
    """Test large file warning is shown."""
    test_file = tmp_path / "large.pdf"
    # Create file > 10MB (11 MB)
    test_file.write_bytes(b"x" * (11 * 1024 * 1024))

    response = {"id": "file-123", "filename": "large.pdf"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=response)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(app, ["rag", "files", "upload", str(test_file)])

        assert result.exit_code == 0
        assert "Uploading: large.pdf" in result.stdout


def test_files_upload_not_a_file(tmp_path, mock_keyring):
    """Test uploading when path is not a file."""
    directory = tmp_path / "notafile"
    directory.mkdir()

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None
        mock_client_factory.return_value = mock_client

        result = runner.invoke(app, ["rag", "files", "upload", str(directory)])

        assert result.exit_code == 0
        assert "Error: Not a file:" in result.stdout
        assert "Summary: 0 successful, 1 failed" in result.stdout


def test_files_delete_confirmation_abort(mock_keyring):
    """Test aborting file deletion via confirmation."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "files", "delete", "file-123"], input="n\n"
        )

        assert result.exit_code == 1  # Abort returns exit code 1


def test_search_validation_empty_query(mock_keyring):
    """Test search rejects empty query."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "", "--collection", "coll-1"],
        )

        assert result.exit_code != 0


def test_search_validation_short_query(mock_keyring):
    """Test search rejects too short query."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "ab", "--collection", "coll-1"],
        )

        assert result.exit_code != 0


def test_search_validation_missing_collection(mock_keyring):
    """Test search requires collection ID."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query"],
        )

        assert result.exit_code != 0


def test_search_validation_invalid_top_k(mock_keyring):
    """Test search validation of top_k parameter."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1", "--top-k", "0"],
        )

        assert result.exit_code != 0


def test_search_validation_high_top_k_warning(mock_keyring):
    """Test search warning for high top_k value."""
    results = {"results": []}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1", "--top-k", "101"],
        )

        assert result.exit_code == 0
        assert "Warning: Requesting more than 100 results" in result.stdout


def test_collections_create_empty_name_validation(mock_keyring):
    """Test collection creation rejects empty name."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "collections", "create", ""],
        )

        assert result.exit_code != 0


def test_files_delete_empty_id_validation(mock_keyring):
    """Test file deletion rejects empty ID."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "files", "delete", "", "--force"],
        )

        assert result.exit_code != 0


def test_collections_delete_empty_id_validation(mock_keyring):
    """Test collection deletion rejects empty ID."""
    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "collections", "delete", "", "--force"],
        )

        assert result.exit_code != 0


def test_search_result_with_text_field(mock_keyring):
    """Test search result using 'text' field instead of 'content'."""
    results = {
        "results": [
            {"text": "Text field result", "distance": 0.1},
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1"],
        )

        assert result.exit_code == 0
        assert "Text field result" in result.stdout


def test_search_result_with_distance_field(mock_keyring):
    """Test search result using 'distance' instead of 'score'."""
    results = {
        "results": [
            {"content": "Result", "distance": 0.05},
        ]
    }

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = _mock_client(post_data=results)
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app,
            ["rag", "search", "query", "--collection", "coll-1"],
        )

        assert result.exit_code == 0
        assert "0.05" in result.stdout


def test_files_upload_multiple_with_mixed_success(tmp_path, mock_keyring):
    """Test uploading multiple files with mixed success/failure."""
    file1 = tmp_path / "success.pdf"
    file2 = tmp_path / "fail.pdf"
    file1.write_text("content1")
    file2.write_text("content2")

    # First upload succeeds, second fails, third succeeds
    response1 = {"id": "file-1", "filename": "success.pdf"}
    response2 = {}  # No ID - will fail
    response3 = {"id": "file-3", "filename": "fail.pdf"}

    with patch("openwebui_cli.commands.rag.create_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.__exit__.return_value = None

        # Mock three upload attempts
        mock_client.post.side_effect = [
            Mock(status_code=200, json=lambda: response1),
            Mock(status_code=200, json=lambda: response2),
            Mock(status_code=200, json=lambda: response3),
        ]
        mock_client_factory.return_value = mock_client

        result = runner.invoke(
            app, ["rag", "files", "upload", str(file1), str(file2)]
        )

        assert result.exit_code == 0
        assert "Uploaded: success.pdf" in result.stdout
        assert "Summary: 1 successful, 1 failed" in result.stdout
