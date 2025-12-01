"""Unit tests for auth module functions."""

from unittest.mock import Mock, patch

import keyring
import pytest

from openwebui_cli.errors import AuthError
from openwebui_cli.http import delete_token, get_token, set_token


@pytest.fixture
def mock_keyring_funcs(monkeypatch):
    """Mock keyring functions."""
    get_password_mock = Mock(return_value=None)
    set_password_mock = Mock()
    delete_password_mock = Mock()

    monkeypatch.setattr("openwebui_cli.http.keyring.get_password", get_password_mock)
    monkeypatch.setattr("openwebui_cli.http.keyring.set_password", set_password_mock)
    monkeypatch.setattr("openwebui_cli.http.keyring.delete_password", delete_password_mock)

    return {
        "get_password": get_password_mock,
        "set_password": set_password_mock,
        "delete_password": delete_password_mock,
    }


def test_get_token_success(mock_keyring_funcs):
    """get_token retrieves token from keyring."""
    mock_keyring_funcs["get_password"].return_value = "stored_token_123"

    token = get_token("default", "http://localhost:8080")

    assert token == "stored_token_123"
    assert mock_keyring_funcs["get_password"].called


def test_get_token_with_special_profile(mock_keyring_funcs):
    """get_token properly formats profile:uri key."""
    mock_keyring_funcs["get_password"].return_value = "test_token"

    get_token("custom_profile", "http://example.com:8080")

    # Verify the key format is correct
    mock_keyring_funcs["get_password"].assert_called_once_with(
        "openwebui-cli", "custom_profile:http://example.com:8080"
    )


def test_get_token_keyring_error(monkeypatch):
    """get_token returns None when keyring is unavailable."""
    monkeypatch.setattr(
        "openwebui_cli.http.keyring.get_password",
        Mock(side_effect=keyring.errors.KeyringError("No backend")),
    )

    token = get_token("default", "http://localhost:8080")

    assert token is None


def test_get_token_returns_none_when_not_stored(mock_keyring_funcs):
    """get_token returns None when token is not in keyring."""
    mock_keyring_funcs["get_password"].return_value = None

    token = get_token("default", "http://localhost:8080")

    assert token is None


def test_set_token_stores_in_keyring(mock_keyring_funcs):
    """set_token stores token in keyring."""
    set_token("default", "http://localhost:8080", "new_token_456")

    mock_keyring_funcs["set_password"].assert_called_once_with(
        "openwebui-cli", "default:http://localhost:8080", "new_token_456"
    )


def test_set_token_with_custom_profile(mock_keyring_funcs):
    """set_token properly formats profile:uri key."""
    set_token("production", "http://prod.example.com", "prod_token")

    mock_keyring_funcs["set_password"].assert_called_once_with(
        "openwebui-cli", "production:http://prod.example.com", "prod_token"
    )


def test_delete_token_removes_from_keyring(mock_keyring_funcs):
    """delete_token removes token from keyring."""
    delete_token("default", "http://localhost:8080")

    mock_keyring_funcs["delete_password"].assert_called_once_with(
        "openwebui-cli", "default:http://localhost:8080"
    )


def test_delete_token_handles_missing_token(mock_keyring_funcs):
    """delete_token gracefully handles missing token."""
    mock_keyring_funcs["delete_password"].side_effect = keyring.errors.PasswordDeleteError("Token not found")

    # Should not raise an exception
    delete_token("default", "http://localhost:8080")


def test_delete_token_with_multiple_profiles(mock_keyring_funcs):
    """delete_token can manage multiple profiles independently."""
    delete_token("profile1", "http://server1:8080")
    delete_token("profile2", "http://server2:8080")

    assert mock_keyring_funcs["delete_password"].call_count == 2
    calls = mock_keyring_funcs["delete_password"].call_args_list
    assert calls[0][0] == ("openwebui-cli", "profile1:http://server1:8080")
    assert calls[1][0] == ("openwebui-cli", "profile2:http://server2:8080")


def test_get_token_unicode_profile(mock_keyring_funcs):
    """get_token handles unicode characters in profile/uri."""
    mock_keyring_funcs["get_password"].return_value = "unicode_token"

    get_token("profil_ée", "http://example.com:8080")

    mock_keyring_funcs["get_password"].assert_called_once()
    call_args = mock_keyring_funcs["get_password"].call_args[0]
    assert "profil_ée" in call_args[1]


def test_set_token_empty_token(mock_keyring_funcs):
    """set_token handles empty token strings."""
    set_token("default", "http://localhost:8080", "")

    mock_keyring_funcs["set_password"].assert_called_once_with(
        "openwebui-cli", "default:http://localhost:8080", ""
    )


def test_token_key_format_consistency(mock_keyring_funcs):
    """Verify consistent key format for profile:uri combinations."""
    profile = "test"
    uri = "http://test.local:9000"
    expected_key = f"{profile}:{uri}"

    set_token(profile, uri, "token1")
    get_token(profile, uri)
    delete_token(profile, uri)

    # Verify all operations use the same key format
    set_call = mock_keyring_funcs["set_password"].call_args[0][1]
    get_call = mock_keyring_funcs["get_password"].call_args[0][1]
    delete_call = mock_keyring_funcs["delete_password"].call_args[0][1]

    assert set_call == expected_key
    assert get_call == expected_key
    assert delete_call == expected_key


def test_get_token_long_token(mock_keyring_funcs):
    """get_token handles very long tokens."""
    long_token = "x" * 10000  # 10KB token
    mock_keyring_funcs["get_password"].return_value = long_token

    token = get_token("default", "http://localhost:8080")

    assert token == long_token
    assert len(token) == 10000


def test_set_token_long_token(mock_keyring_funcs):
    """set_token handles very long tokens."""
    long_token = "y" * 10000

    set_token("default", "http://localhost:8080", long_token)

    call_args = mock_keyring_funcs["set_password"].call_args[0]
    assert call_args[2] == long_token
    assert len(call_args[2]) == 10000


def test_get_token_special_characters_in_uri(mock_keyring_funcs):
    """get_token handles special characters in URIs."""
    mock_keyring_funcs["get_password"].return_value = "special_token"

    uri = "http://user:pass@example.com:8080/path?query=value&other=123"
    get_token("default", uri)

    call_args = mock_keyring_funcs["get_password"].call_args[0]
    assert uri in call_args[1]


def test_multiple_get_token_calls_with_cache(mock_keyring_funcs):
    """get_token makes fresh calls each time (no internal caching)."""
    mock_keyring_funcs["get_password"].side_effect = ["token1", "token2", "token1"]

    token1 = get_token("default", "http://localhost:8080")
    token2 = get_token("default", "http://localhost:8080")
    token3 = get_token("default", "http://localhost:8080")

    assert token1 == "token1"
    assert token2 == "token2"
    assert token3 == "token1"
    assert mock_keyring_funcs["get_password"].call_count == 3
