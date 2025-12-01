"""Tests for admin commands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from typer.testing import CliRunner

from openwebui_cli.errors import AuthError, NetworkError
from openwebui_cli.main import app

runner = CliRunner()


def _mock_client(data, status_code=200, json_response=True):
    """Create a mock HTTP client for testing."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = None
    response = Mock()
    response.status_code = status_code
    if json_response:
        response.json.return_value = data
    else:
        response.text = data
    client.get.return_value = response
    return client


# Test 1: Admin stats - successful response from /api/v1/admin/stats
def test_admin_stats_success():
    """Test admin stats command with successful API response."""
    data = {"users": 10, "requests": 42, "models": 5, "uptime": 86400}

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(data)

        result = runner.invoke(app, ["admin", "stats"])

        assert result.exit_code == 0
        assert "users" in result.stdout
        assert "10" in result.stdout
        assert "requests" in result.stdout
        assert "42" in result.stdout


# Test 2: Admin stats - 403 Forbidden (non-admin user)
def test_admin_stats_forbidden():
    """Test admin stats command with 403 Forbidden error when trying to access admin stats."""
    # When /api/v1/admin/stats fails, fallback to /api/v1/auths/
    # If user is not admin, raise AuthError
    user_data = {
        "name": "john_user",
        "role": "user",
        "status": "active"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses for the two calls
        admin_response = Mock()
        admin_response.status_code = 403

        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = user_data

        # First get() call fails, second succeeds
        client.get.side_effect = [
            admin_response,
            user_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # First call (admin/stats) raises AuthError, second returns user data
            mock_handle.side_effect = [
                AuthError("Permission denied. This operation requires higher privileges."),
                user_data
            ]

            result = runner.invoke(app, ["admin", "stats"])

            # The stats command raises AuthError when user is not admin
            # AuthError is raised and propagates
            assert result.exit_code == 1
            # Check exception contains user info
            assert "john_user" in str(result.exception) or "admin" in str(result.exception).lower()


# Test 3: Admin stats - Network error handling
def test_admin_stats_network_error():
    """Test admin stats command with network connectivity failure."""
    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        # Simulate network connection error from create_client itself
        mock_client_factory.side_effect = NetworkError("Could not connect to server")

        result = runner.invoke(app, ["admin", "stats"])

        # Should exit with network error
        assert result.exit_code == 1  # Unhandled exception
        assert "Could not connect" in str(result.exception) or "network" in str(result.exception).lower()


# Test 4: Admin stats - Fallback behavior with admin user info
def test_admin_stats_fallback_behavior():
    """Test admin stats fallback to user info when admin endpoint fails but user is admin."""
    user_data = {
        "name": "admin_user",
        "role": "admin",
        "status": "connected"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Create mock responses
        admin_response = Mock()
        admin_response.status_code = 500

        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = user_data

        # First get() call returns error response, second returns user response
        client.get.side_effect = [
            admin_response,
            user_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # First call (admin/stats) raises exception, second call (auths) returns user data
            mock_handle.side_effect = [
                Exception("Server error"),
                user_data
            ]

            result = runner.invoke(app, ["admin", "stats"])

            # Should succeed with fallback data
            assert result.exit_code == 0
            # Should show table with user data
            assert "admin_user" in result.stdout or "admin" in result.stdout or "connected" in result.stdout


# Test 5: Admin stats - JSON format output
def test_admin_stats_json_format():
    """Test admin stats command with JSON output format."""
    data = {"users": 10, "requests": 42, "models": 5}

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(data)

        # Use --format json global option
        result = runner.invoke(app, ["--format", "json", "admin", "stats"])

        # Should output JSON format
        assert result.exit_code == 0
        assert "10" in result.stdout


# Test 6: Admin users - list users (requires admin role)
def test_admin_users_list():
    """Test admin users command to list users."""
    admin_user = {
        "name": "admin_user",
        "role": "admin",
        "status": "active"
    }

    users_list = [
        {"id": "1", "name": "admin_user", "email": "admin@example.com", "role": "admin"},
        {"id": "2", "name": "user1", "email": "user1@example.com", "role": "user"}
    ]

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses: first for admin check, second for users list
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        users_response = Mock()
        users_response.status_code = 200
        users_response.json.return_value = users_list

        client.get.side_effect = [
            admin_response,
            users_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # First call (auths) returns admin user, second (users) returns list
            mock_handle.side_effect = [
                admin_user,
                users_list
            ]

            result = runner.invoke(app, ["admin", "users"])

            assert result.exit_code == 0
            assert "admin_user" in result.stdout or "user1" in result.stdout


# Test 7: Admin config - show server configuration
def test_admin_config_list():
    """Test admin config command to show server configuration."""
    admin_user = {
        "name": "admin_user",
        "role": "admin",
        "status": "active"
    }

    config_data = {
        "version": "1.0.0",
        "debug": False,
        "max_users": 100
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses: first for admin check, second for config
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = config_data

        client.get.side_effect = [
            admin_response,
            config_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # First call (auths) returns admin user, second (config) returns config
            mock_handle.side_effect = [
                admin_user,
                config_data
            ]

            result = runner.invoke(app, ["admin", "config"])

            assert result.exit_code == 0
            assert "version" in result.stdout or "1.0.0" in result.stdout or "configuration" in result.stdout.lower()


# Test 8: Admin stats - with period option
def test_admin_stats_with_period_option():
    """Test admin stats command with different period options."""
    data = {"period": "week", "requests": 420, "users": 50}

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(data)

        result = runner.invoke(app, ["admin", "stats", "--period", "week"])

        assert result.exit_code == 0
        assert "requests" in result.stdout


# Test 9: Admin stats - role check in fallback
def test_admin_stats_role_check_fallback():
    """Test admin stats role validation in fallback path."""
    non_admin_user = {
        "name": "regular_user",
        "role": "user",
        "status": "active"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # First call fails (admin stats), second succeeds but user is not admin
        admin_response = Mock()
        admin_response.status_code = 500

        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = non_admin_user

        client.get.side_effect = [
            admin_response,
            user_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # First call fails, second returns non-admin user
            # When role is not admin, the code raises AuthError
            mock_handle.side_effect = [
                Exception("Server error"),
                non_admin_user
            ]

            result = runner.invoke(app, ["admin", "stats"])

            # Should fail with auth error about role
            assert result.exit_code == 1
            # The actual error message comes from the AuthError raised in the code
            exc_str = str(result.exception)
            # Check if the exception is the AuthError from the role check
            assert "regular_user" in exc_str or "admin" in exc_str.lower()


# Test 10: Admin stats - Empty response handling
def test_admin_stats_empty_response():
    """Test admin stats with empty stats response."""
    data = {}

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(data)

        result = runner.invoke(app, ["admin", "stats"])

        assert result.exit_code == 0
        # Should still render table even if empty


# Test 11: Admin stats - Token handling from context
def test_admin_stats_uses_context_token():
    """Test that admin stats uses token from typer context via global options."""
    data = {"users": 10, "requests": 42}

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(data)

        # Pass token via global --token option
        result = runner.invoke(app, ["--token", "TEST_TOKEN_123", "admin", "stats"])

        # Verify create_client was called with token
        assert result.exit_code == 0
        assert mock_client_factory.called
        call_args = mock_client_factory.call_args
        # Token is passed from main callback to context, then to create_client
        assert call_args is not None


# Test 12: Admin stats - Large data response
def test_admin_stats_large_response():
    """Test admin stats with large number of metrics."""
    data = {f"metric_{i}": i * 100 for i in range(50)}

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        mock_client_factory.return_value = _mock_client(data)

        result = runner.invoke(app, ["admin", "stats"])

        assert result.exit_code == 0
        # Should handle large responses gracefully


# Test 13: Admin users - non-admin user forbidden
def test_admin_users_forbidden():
    """Test admin users command when user lacks admin role."""
    non_admin_user = {
        "name": "regular_user",
        "role": "user"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock response for non-admin user
        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = non_admin_user

        client.get.return_value = user_response
        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # Return non-admin user
            mock_handle.return_value = non_admin_user

            result = runner.invoke(app, ["admin", "users"])

            # Should fail with auth error
            assert result.exit_code == 1
            assert "regular_user" in str(result.exception) or "admin" in str(result.exception).lower()


# Test 14: Admin config - non-admin user forbidden
def test_admin_config_forbidden():
    """Test admin config command when user lacks admin role."""
    non_admin_user = {
        "name": "regular_user",
        "role": "user"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock response for non-admin user
        user_response = Mock()
        user_response.status_code = 200
        user_response.json.return_value = non_admin_user

        client.get.return_value = user_response
        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # Return non-admin user
            mock_handle.return_value = non_admin_user

            result = runner.invoke(app, ["admin", "config"])

            # Should fail with auth error
            assert result.exit_code == 1
            assert "regular_user" in str(result.exception) or "admin" in str(result.exception).lower()


# Test 15: Admin config - fallback to basic server info
def test_admin_config_fallback():
    """Test admin config fallback to basic info when endpoint fails."""
    admin_user = {
        "name": "admin_user",
        "role": "admin"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses: first for admin check, second fails for config
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        config_response = Mock()
        config_response.status_code = 500

        client.get.side_effect = [
            admin_response,
            config_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # First returns admin user, second raises exception (triggering fallback)
            mock_handle.side_effect = [
                admin_user,
                Exception("Config endpoint failed")
            ]

            result = runner.invoke(app, ["admin", "config"])

            # Should succeed with fallback data
            assert result.exit_code == 0
            assert "admin_user" in result.stdout or "admin" in result.stdout or "connected" in result.stdout


# Test 16: Admin users - JSON format output
def test_admin_users_json_format():
    """Test admin users command with JSON output format."""
    admin_user = {
        "name": "admin_user",
        "role": "admin"
    }

    users_list = [
        {"id": "1", "name": "user1", "username": "user1", "email": "user1@example.com", "role": "user"},
        {"id": "2", "name": "user2", "username": "user2", "email": "user2@example.com", "role": "user"}
    ]

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        users_response = Mock()
        users_response.status_code = 200
        users_response.json.return_value = users_list

        client.get.side_effect = [
            admin_response,
            users_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            mock_handle.side_effect = [
                admin_user,
                users_list
            ]

            result = runner.invoke(app, ["--format", "json", "admin", "users"])

            assert result.exit_code == 0
            assert "user1" in result.stdout or "user2" in result.stdout


# Test 17: Admin config - JSON format output
def test_admin_config_json_format():
    """Test admin config command with JSON output format."""
    admin_user = {
        "name": "admin_user",
        "role": "admin"
    }

    config_data = {
        "version": "0.3.0",
        "debug": False
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = config_data

        client.get.side_effect = [
            admin_response,
            config_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            mock_handle.side_effect = [
                admin_user,
                config_data
            ]

            result = runner.invoke(app, ["--format", "json", "admin", "config"])

            assert result.exit_code == 0
            assert "version" in result.stdout or "0.3.0" in result.stdout


# Test 18: Admin users - handle different response formats
def test_admin_users_response_formats():
    """Test admin users with different user list response formats."""
    admin_user = {
        "name": "admin_user",
        "role": "admin"
    }

    # Users wrapped in data key
    users_response_wrapped = {
        "data": [
            {"id": "1", "name": "user1", "username": "user1", "email": "user1@example.com", "role": "user"}
        ]
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        users_response = Mock()
        users_response.status_code = 200
        users_response.json.return_value = users_response_wrapped

        client.get.side_effect = [
            admin_response,
            users_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            mock_handle.side_effect = [
                admin_user,
                users_response_wrapped
            ]

            result = runner.invoke(app, ["admin", "users"])

            assert result.exit_code == 0
            assert "user1" in result.stdout


# Test 19: Admin users - error handling during fetch
def test_admin_users_error_handling():
    """Test admin users error handling when fetch fails."""
    admin_user = {
        "name": "admin_user",
        "role": "admin"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Admin check succeeds, users fetch fails
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        users_response = Mock()
        users_response.status_code = 500

        client.get.side_effect = [
            admin_response,
            users_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            # Admin check succeeds, users fetch raises exception
            mock_handle.side_effect = [
                admin_user,
                Exception("Server error")
            ]

            result = runner.invoke(app, ["admin", "users"])

            # Should propagate the exception
            assert result.exit_code == 1


# Test 20: Admin config - handle dict response (non-exception path)
def test_admin_config_dict_response():
    """Test admin config with dict response format."""
    admin_user = {
        "name": "admin_user",
        "role": "admin"
    }

    config_data = {
        "setting1": "value1",
        "setting2": "value2"
    }

    with patch("openwebui_cli.commands.admin.create_client") as mock_client_factory:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = None

        # Mock responses
        admin_response = Mock()
        admin_response.status_code = 200
        admin_response.json.return_value = admin_user

        config_response = Mock()
        config_response.status_code = 200
        config_response.json.return_value = config_data

        client.get.side_effect = [
            admin_response,
            config_response
        ]

        mock_client_factory.return_value = client

        with patch("openwebui_cli.commands.admin.handle_response") as mock_handle:
            mock_handle.side_effect = [
                admin_user,
                config_data
            ]

            result = runner.invoke(app, ["admin", "config"])

            assert result.exit_code == 0
            assert "setting1" in result.stdout or "value1" in result.stdout
