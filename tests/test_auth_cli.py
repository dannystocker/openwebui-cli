"""CLI-level tests for auth commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import httpx
import keyring
import pytest
from typer.testing import CliRunner

from openwebui_cli.main import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def mock_config(tmp_path, monkeypatch):
    """Use a temp config dir to avoid touching the real filesystem."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"
    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    from openwebui_cli.config import Config, save_config

    save_config(Config())
    return config_path


@pytest.fixture
def mock_keyring(monkeypatch):
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


@pytest.fixture
def mock_create_client(monkeypatch):
    """Mock create_client to return a mocked httpx.Client."""

    def _create_mock_client():
        client_mock = MagicMock(spec=httpx.Client)
        return client_mock

    return _create_mock_client


# Test login success
def test_login_success(mock_keyring, monkeypatch):
    """Login command stores token when successful."""
    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"token": "test_token_123", "name": "Test User"}

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(
        app,
        ["auth", "login", "--username", "testuser", "--password", "testpass"],
    )

    assert result.exit_code == 0
    assert "Successfully logged in as Test User" in result.stdout
    assert mock_keyring["set_password"].called


# Test login failure
def test_login_failure_401(mock_keyring, monkeypatch):
    """Login command handles 401 error from server."""
    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 401
    response_mock.text = "Unauthorized"

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(
        app,
        ["auth", "login", "--username", "testuser", "--password", "wrongpass"],
    )

    assert result.exit_code != 0


# Test login with no token in response
def test_login_no_token_received(mock_keyring, monkeypatch):
    """Login command handles missing token in response."""
    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"name": "Test User"}  # No token field

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(
        app,
        ["auth", "login", "--username", "testuser", "--password", "testpass"],
    )

    assert result.exit_code != 0


# Test login with env token precedence
def test_login_with_env_token_override(monkeypatch, tmp_path):
    """Verify OPENWEBUI_TOKEN env var takes precedence."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"
    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    from openwebui_cli.config import Config, save_config

    save_config(Config())

    monkeypatch.setenv("OPENWEBUI_TOKEN", "env_token_value")

    # Mock keyring to raise error - env token should take precedence
    monkeypatch.setattr("openwebui_cli.http.keyring.get_password", Mock(side_effect=keyring.errors.KeyringError()))

    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"name": "Test User", "email": "test@example.com", "role": "user"}

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.get.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code == 0
    assert "User: Test User" in result.stdout


# Test login no keyring available
def test_login_no_keyring_fallback(mock_keyring, monkeypatch):
    """Login handles keyring unavailability gracefully."""
    # Mock keyring to raise error
    mock_keyring["set_password"].side_effect = keyring.errors.KeyringError("No backend")

    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"token": "test_token_123", "name": "Test User"}

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(
        app,
        ["auth", "login", "--username", "testuser", "--password", "testpass"],
    )

    # Should still show error about keyring
    assert result.exit_code != 0


# Test logout
def test_logout_removes_token(mock_keyring, monkeypatch):
    """Logout command removes token from keyring."""
    result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "Logged out" in result.stdout
    assert mock_keyring["delete_password"].called


# Test whoami with valid token
def test_whoami_with_token(mock_keyring, monkeypatch):
    """whoami command displays user info when token is valid."""
    mock_keyring["get_password"].return_value = "valid_token"

    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {
        "name": "John Doe",
        "email": "john@example.com",
        "role": "admin",
    }

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.get.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code == 0
    assert "John Doe" in result.stdout
    assert "john@example.com" in result.stdout
    assert "admin" in result.stdout


# Test whoami with missing fields
def test_whoami_missing_fields(mock_keyring, monkeypatch):
    """whoami displays Unknown for missing fields."""
    mock_keyring["get_password"].return_value = "valid_token"

    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"name": "Jane Doe"}  # Missing email, role

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.get.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code == 0
    assert "Jane Doe" in result.stdout
    assert "Unknown" in result.stdout


# Test whoami without token
def test_whoami_no_token(mock_keyring, monkeypatch):
    """whoami fails when no token is available."""
    mock_keyring["get_password"].return_value = None
    monkeypatch.delenv("OPENWEBUI_TOKEN", raising=False)

    monkeypatch.setattr(
        "openwebui_cli.commands.auth.create_client",
        Mock(side_effect=Exception("No authentication token available")),
    )

    result = runner.invoke(app, ["auth", "whoami"])

    assert result.exit_code != 0


# Test token command show flag
def test_token_show_full_token(mock_keyring, monkeypatch):
    """Token command with --show displays full token."""
    mock_keyring["get_password"].return_value = "very_long_test_token_1234567890"

    monkeypatch.setattr(
        "openwebui_cli.config.Settings",
        lambda: SimpleNamespace(
            openwebui_token=None, openwebui_profile=None, openwebui_uri=None
        ),
    )
    monkeypatch.setattr("openwebui_cli.commands.auth.get_token", lambda *args, **kwargs: "very_long_test_token_1234567890")

    result = runner.invoke(app, ["auth", "token", "--show"])

    assert result.exit_code == 0
    assert "very_long_test_token_1234567890" in result.stdout


# Test token command without show flag
def test_token_masked(mock_keyring, monkeypatch):
    """Token command masks token when --show not provided."""
    test_token = "very_long_test_token_1234567890"

    monkeypatch.setattr(
        "openwebui_cli.config.Settings",
        lambda: SimpleNamespace(
            openwebui_token=None, openwebui_profile=None, openwebui_uri=None
        ),
    )
    monkeypatch.setattr("openwebui_cli.commands.auth.get_token", lambda *args, **kwargs: test_token)

    result = runner.invoke(app, ["auth", "token"])

    assert result.exit_code == 0
    assert "7890" in result.stdout  # Last 4 chars visible
    assert "..." in result.stdout  # Dots indicating masking
    assert test_token not in result.stdout  # Full token not visible


# Test token command no token
def test_token_no_token_available(mock_keyring, monkeypatch):
    """Token command shows message when no token available."""
    mock_keyring["get_password"].return_value = None

    monkeypatch.setattr(
        "openwebui_cli.config.Settings",
        lambda: SimpleNamespace(
            openwebui_token=None, openwebui_profile=None, openwebui_uri=None
        ),
    )
    monkeypatch.setattr("openwebui_cli.commands.auth.get_token", lambda *args, **kwargs: None)

    result = runner.invoke(app, ["auth", "token"])

    assert result.exit_code == 0
    assert "No token found" in result.stdout


# Test refresh token
def test_refresh_token_success(mock_keyring, monkeypatch):
    """Refresh command successfully refreshes token."""
    mock_keyring["get_password"].return_value = "old_token"

    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"token": "new_refreshed_token"}

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(app, ["auth", "refresh"])

    assert result.exit_code == 0
    assert "Token refreshed successfully" in result.stdout
    assert mock_keyring["set_password"].called


# Test refresh token no new token
def test_refresh_token_no_new_token(mock_keyring, monkeypatch):
    """Refresh handles response without new token."""
    mock_keyring["get_password"].return_value = "old_token"

    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {}  # No token in response

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(app, ["auth", "refresh"])

    assert result.exit_code == 0
    assert "No new token received" in result.stdout


# Test token command with short token
def test_token_short_token_masked(monkeypatch, tmp_path):
    """Token command shows *** for short tokens."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"
    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    from openwebui_cli.config import Config, save_config

    save_config(Config())

    # Mock Settings to return a short token
    monkeypatch.setattr(
        "openwebui_cli.commands.auth.Settings",
        lambda: SimpleNamespace(
            openwebui_token="short", openwebui_profile=None, openwebui_uri=None
        ),
    )
    monkeypatch.setattr("openwebui_cli.commands.auth.get_token", lambda *args, **kwargs: None)

    result = runner.invoke(app, ["auth", "token"])

    assert result.exit_code == 0
    assert "***" in result.stdout


# Test login prompts for credentials
def test_login_prompts_for_credentials(mock_keyring, monkeypatch):
    """Login prompts for username and password if not provided."""
    response_mock = MagicMock(spec=httpx.Response)
    response_mock.status_code = 200
    response_mock.json.return_value = {"token": "test_token", "name": "Test User"}

    client_mock = MagicMock(spec=httpx.Client)
    client_mock.post.return_value = response_mock
    client_mock.__enter__ = Mock(return_value=client_mock)
    client_mock.__exit__ = Mock(return_value=False)

    monkeypatch.setattr("openwebui_cli.commands.auth.create_client", lambda **kwargs: client_mock)

    result = runner.invoke(
        app,
        ["auth", "login"],
        input="testuser\ntestpass\n",
    )

    # Should complete without error (prompts are handled by typer)
    assert mock_keyring["set_password"].called or result.exit_code == 0


# Test refresh token with error
def test_refresh_token_error_handling(mock_keyring, monkeypatch):
    """Refresh command handles errors gracefully."""
    mock_keyring["get_password"].return_value = "old_token"

    # Mock create_client to raise an exception during refresh
    monkeypatch.setattr(
        "openwebui_cli.commands.auth.create_client",
        Mock(side_effect=httpx.ConnectError("Connection failed")),
    )

    result = runner.invoke(app, ["auth", "refresh"])

    assert result.exit_code != 0


# Test login with network error
def test_login_network_error(mock_keyring, monkeypatch):
    """Login command handles network errors."""
    monkeypatch.setattr(
        "openwebui_cli.commands.auth.create_client",
        Mock(side_effect=httpx.ConnectError("Could not connect to server")),
    )

    result = runner.invoke(
        app,
        ["auth", "login", "--username", "testuser", "--password", "testpass"],
    )

    assert result.exit_code != 0


def test_auth_token_env_fallback(monkeypatch):
    """Token command should respect OPENWEBUI_TOKEN env even without keyring."""
    monkeypatch.setenv("OPENWEBUI_TOKEN", "ENV_TOKEN")
    monkeypatch.setattr(
        "openwebui_cli.config.Settings",
        lambda: SimpleNamespace(
            openwebui_token="ENV_TOKEN", openwebui_profile=None, openwebui_uri=None
        ),
    )
    monkeypatch.setattr("openwebui_cli.commands.auth.get_token", lambda *args, **kwargs: None)

    result = runner.invoke(app, ["auth", "token", "--show"])

    assert result.exit_code == 0
    assert "ENV_TOKEN" in result.stdout
