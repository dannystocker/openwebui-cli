"""Tests for HTTP client helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import httpx
import keyring
import pytest

from openwebui_cli.config import Config
from openwebui_cli.errors import AuthError, NetworkError, ServerError
from openwebui_cli.http import (
    create_async_client,
    create_client,
    delete_token,
    get_token,
    handle_request_error,
    handle_response,
    set_token,
)


@pytest.fixture(autouse=True)
def stub_config(monkeypatch):
    """Avoid reading real config files during tests."""
    monkeypatch.setattr("openwebui_cli.http.load_config", lambda: Config())
    monkeypatch.setattr(
        "openwebui_cli.http.get_effective_config", lambda profile, uri: ("http://api", "default")
    )


# ============================================================================
# Token Management Tests
# ============================================================================


def test_get_token_success(monkeypatch):
    """Retrieve token from keyring successfully."""
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password",
        lambda service, key: "stored_token" if key == "default:http://api" else None,
    )
    token = get_token("default", "http://api")
    assert token == "stored_token"


def test_get_token_keyring_error(monkeypatch):
    """Handle keyring unavailability gracefully."""
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password",
        Mock(side_effect=keyring.errors.KeyringError("no backend")),
    )
    token = get_token("default", "http://api")
    assert token is None


def test_set_token_success(monkeypatch):
    """Store token in keyring."""
    mock_set = Mock()
    monkeypatch.setattr("openwebui_cli.http.keyring.set_password", mock_set)

    set_token("default", "http://api", "new_token")
    mock_set.assert_called_once_with("openwebui-cli", "default:http://api", "new_token")


def test_delete_token_success(monkeypatch):
    """Delete token from keyring."""
    mock_delete = Mock()
    monkeypatch.setattr("openwebui_cli.http.keyring.delete_password", mock_delete)

    delete_token("default", "http://api")
    mock_delete.assert_called_once_with("openwebui-cli", "default:http://api")


def test_delete_token_not_found(monkeypatch):
    """Handle deletion of non-existent token gracefully."""
    mock_delete = Mock(side_effect=keyring.errors.PasswordDeleteError("not found"))
    monkeypatch.setattr("openwebui_cli.http.keyring.delete_password", mock_delete)

    # Should not raise
    delete_token("default", "http://api")
    mock_delete.assert_called_once()


# ============================================================================
# Client Creation Tests - Token Precedence
# ============================================================================


def test_create_client_prefers_cli_token(monkeypatch):
    """CLI-provided token should skip keyring entirely."""

    def raise_keyring(*_, **__):
        raise keyring.errors.NoKeyringError()

    monkeypatch.setattr("openwebui_cli.http.keyring.get_password", raise_keyring)

    client = create_client(token="TOKEN123")
    assert isinstance(client, httpx.Client)
    assert client.headers["Authorization"] == "Bearer TOKEN123"


def test_create_client_uses_env_token(monkeypatch):
    """Environment variable token takes precedence over keyring."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token="ENV_TOKEN")
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: "keyring_token"
    )

    client = create_client()
    assert client.headers["Authorization"] == "Bearer ENV_TOKEN"


def test_create_client_falls_back_to_keyring(monkeypatch):
    """Falls back to keyring when env token not available."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: "KEYRING_TOKEN"
    )

    client = create_client()
    assert client.headers["Authorization"] == "Bearer KEYRING_TOKEN"


def test_create_client_allow_unauthenticated(monkeypatch):
    """Allow unauthenticated client creation when explicitly requested."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: None
    )

    client = create_client(allow_unauthenticated=True)
    assert isinstance(client, httpx.Client)
    assert "Authorization" not in client.headers


def test_create_client_requires_token(monkeypatch):
    """Token is required unless allow_unauthenticated is set."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: None
    )

    with pytest.raises(AuthError):
        create_client()


def test_create_client_keyring_error_without_fallback(monkeypatch):
    """Raise AuthError when keyring fails and no other token source."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password",
        Mock(side_effect=keyring.errors.KeyringError("no backend")),
    )

    with pytest.raises(AuthError):
        create_client()


# ============================================================================
# Client Configuration Tests
# ============================================================================


def test_create_client_sets_base_url(monkeypatch):
    """Client should have correct base URL."""
    monkeypatch.setattr(
        "openwebui_cli.http.get_effective_config", lambda *args, **kwargs: ("http://test.local", "default")
    )
    client = create_client(token="TOKEN")
    assert client.base_url == "http://test.local"


def test_create_client_sets_default_headers(monkeypatch):
    """Client should have standard headers."""
    client = create_client(token="TOKEN")
    assert client.headers["Content-Type"] == "application/json"
    assert client.headers["Accept"] == "application/json"


def test_create_client_uses_custom_timeout(monkeypatch):
    """Client should use custom timeout when provided."""
    client = create_client(token="TOKEN", timeout=60.0)
    assert client.timeout == httpx.Timeout(60.0)


def test_create_client_uses_config_default_timeout(monkeypatch):
    """Client should use config default timeout when not specified."""
    config = Config()
    config.defaults.timeout = 45
    monkeypatch.setattr("openwebui_cli.http.load_config", lambda: config)

    client = create_client(token="TOKEN")
    assert client.timeout == httpx.Timeout(45)


def test_create_client_with_profile_and_uri(monkeypatch):
    """Client should accept profile and URI parameters."""
    monkeypatch.setattr(
        "openwebui_cli.http.get_effective_config",
        lambda profile, uri: ("http://custom.local", "custom"),
    )
    client = create_client(profile="custom", uri="http://custom.local", token="TOKEN")
    assert isinstance(client, httpx.Client)


# ============================================================================
# Async Client Tests
# ============================================================================


def test_create_async_client_with_token(monkeypatch):
    """Create async client with CLI token."""
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: None
    )

    client = create_async_client(token="ASYNC_TOKEN")
    assert isinstance(client, httpx.AsyncClient)
    assert client.headers["Authorization"] == "Bearer ASYNC_TOKEN"


def test_create_async_client_token_precedence(monkeypatch):
    """Async client should follow same token precedence."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token="ENV_TOKEN")
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: "KEYRING_TOKEN"
    )

    client = create_async_client()
    assert client.headers["Authorization"] == "Bearer ENV_TOKEN"


def test_create_async_client_allow_unauthenticated(monkeypatch):
    """Async client should allow unauthenticated mode."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: None
    )

    client = create_async_client(allow_unauthenticated=True)
    assert isinstance(client, httpx.AsyncClient)
    assert "Authorization" not in client.headers


def test_create_async_client_requires_token(monkeypatch):
    """Async client should require token unless explicitly allowed."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: None
    )

    with pytest.raises(AuthError):
        create_async_client()


# ============================================================================
# Response Handling Tests
# ============================================================================


def test_handle_response_success_json():
    """Parse successful JSON response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = {"result": "success", "data": [1, 2, 3]}

    result = handle_response(response)
    assert result == {"result": "success", "data": [1, 2, 3]}


def test_handle_response_success_empty():
    """Handle response with no JSON body."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.side_effect = ValueError("No JSON")
    response.text = "Plain text response"

    result = handle_response(response)
    assert result == {"text": "Plain text response"}


def test_handle_response_401_unauthorized():
    """Handle 401 Unauthorized response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 401

    with pytest.raises(AuthError, match="Authentication required"):
        handle_response(response)


def test_handle_response_403_forbidden():
    """Handle 403 Forbidden response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 403

    with pytest.raises(AuthError, match="Permission denied"):
        handle_response(response)


def test_handle_response_404_not_found_with_detail():
    """Handle 404 with JSON error detail."""
    response = Mock(spec=httpx.Response)
    response.status_code = 404
    response.json.return_value = {"detail": "Model not found"}

    with pytest.raises(ServerError, match="Model not found"):
        handle_response(response)


def test_handle_response_404_not_found_with_message():
    """Handle 404 with message field in JSON."""
    response = Mock(spec=httpx.Response)
    response.status_code = 404
    response.json.return_value = {"message": "Resource missing"}

    with pytest.raises(ServerError, match="Resource missing"):
        handle_response(response)


def test_handle_response_404_not_found_plain_text():
    """Handle 404 without JSON body."""
    response = Mock(spec=httpx.Response)
    response.status_code = 404
    response.json.side_effect = ValueError("No JSON")

    with pytest.raises(ServerError, match="Resource not found"):
        handle_response(response)


def test_handle_response_500_server_error():
    """Handle 500 Server Error response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 500
    response.text = "Internal server error"

    with pytest.raises(ServerError, match="Server error.*500"):
        handle_response(response)


def test_handle_response_502_bad_gateway():
    """Handle 502 Bad Gateway response."""
    response = Mock(spec=httpx.Response)
    response.status_code = 502
    response.text = "Bad gateway"

    with pytest.raises(ServerError, match="Server error"):
        handle_response(response)


def test_handle_response_400_bad_request_with_detail():
    """Handle 400 Bad Request with error detail."""
    response = Mock(spec=httpx.Response)
    response.status_code = 400
    response.json.return_value = {"detail": "Invalid parameter"}

    with pytest.raises(ServerError, match="Invalid parameter"):
        handle_response(response)


def test_handle_response_400_bad_request_plain_text():
    """Handle 400 Bad Request without JSON."""
    response = Mock(spec=httpx.Response)
    response.status_code = 400
    response.json.side_effect = ValueError("No JSON")
    response.text = "Bad request body"

    with pytest.raises(ServerError, match="Bad request body"):
        handle_response(response)


# ============================================================================
# Request Error Handling Tests
# ============================================================================


def test_handle_request_error_keyring():
    """Keyring errors are converted to AuthError with guidance."""
    with pytest.raises(AuthError, match="Keyring is unavailable"):
        handle_request_error(keyring.errors.KeyringError("no backend"))


def test_handle_request_error_connect():
    """Connection errors are converted to NetworkError."""
    error = httpx.ConnectError("Failed to connect")
    with pytest.raises(NetworkError, match="Could not connect"):
        handle_request_error(error)


def test_handle_request_error_timeout():
    """Timeout errors are converted to NetworkError."""
    error = httpx.TimeoutException("Request timed out")
    with pytest.raises(NetworkError, match="Request timed out"):
        handle_request_error(error)


def test_handle_request_error_generic_request_error():
    """Generic httpx request errors converted to NetworkError."""
    error = httpx.RequestError("Generic request error")
    with pytest.raises(NetworkError, match="Request failed"):
        handle_request_error(error)


def test_handle_request_error_other():
    """Non-httpx errors are re-raised."""
    error = ValueError("Some unexpected error")
    with pytest.raises(ValueError):
        handle_request_error(error)


def test_handle_request_error_network_error_specific():
    """Test specific network timeout guidance."""
    error = httpx.TimeoutException("Timeout after 30s")
    with pytest.raises(NetworkError, match="Increase timeout"):
        handle_request_error(error)


# ============================================================================
# Integration Tests
# ============================================================================


def test_client_complete_flow(monkeypatch):
    """Test complete client creation and usage flow."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token=None)
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: "STORED_TOKEN"
    )

    # Create client with keyring token
    client = create_client()
    assert client.headers["Authorization"] == "Bearer STORED_TOKEN"
    assert client.base_url == "http://api"


def test_client_cli_token_overrides_all(monkeypatch):
    """CLI token should override all other sources."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token="ENV_TOKEN")
    )
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password", lambda *args, **kwargs: "KEYRING_TOKEN"
    )

    # CLI token should win
    client = create_client(token="CLI_TOKEN")
    assert client.headers["Authorization"] == "Bearer CLI_TOKEN"


def test_async_client_complete_flow(monkeypatch):
    """Test async client creation and configuration."""
    monkeypatch.setattr(
        "openwebui_cli.config.Settings", lambda: SimpleNamespace(openwebui_token="ASYNC_TOKEN")
    )

    client = create_async_client()
    assert isinstance(client, httpx.AsyncClient)
    assert client.headers["Authorization"] == "Bearer ASYNC_TOKEN"
    assert client.base_url == "http://api"
