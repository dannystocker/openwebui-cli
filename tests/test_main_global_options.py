"""Tests for main CLI global options stored in context."""

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


@pytest.fixture
def mock_client():
    """Mock HTTP client for testing."""
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


class TestGlobalOptionsStorage:
    """Test that global options are properly stored in context."""

    def test_profile_option_stored_in_context(self, mock_config, mock_keyring, mock_client):
        """Test --profile option is stored in context."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--profile", "test-profile",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify profile was passed to create_client
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "test-profile"

    def test_uri_option_stored_in_context(self, mock_config, mock_keyring, mock_client):
        """Test --uri option is stored in context."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--uri", "http://test.local:9000",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify URI was passed to create_client
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("uri") == "http://test.local:9000"

    def test_token_option_stored_in_context(self, mock_config, mock_keyring, mock_client):
        """Test --token option is stored in context."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--token", "secret-token-123",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify token was passed to create_client
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("token") == "secret-token-123"

    def test_timeout_option_stored_in_context(self, mock_config, mock_keyring, mock_client):
        """Test --timeout option is stored in context."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--timeout", "60",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify timeout was passed to create_client as integer
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("timeout") == 60
            assert isinstance(call_kwargs.get("timeout"), int)

    def test_format_option_stored_in_context(self, mock_config, mock_keyring, mock_client):
        """Test --format option is stored in context."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--format", "json",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Verify format was used for output
            assert "choices" in result.stdout  # JSON output has 'choices' key


class TestFormatOptionDefault:
    """Test format option defaults to 'text'."""

    def test_format_defaults_to_text(self, mock_config, mock_keyring, mock_client):
        """Test --format defaults to 'text' when not specified."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Text format should show plain content without JSON structure
            assert "Test response" in result.stdout

    def test_format_text_explicit(self, mock_config, mock_keyring, mock_client):
        """Test --format text explicitly."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--format", "text",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            assert "Test response" in result.stdout

    def test_format_json_explicit(self, mock_config, mock_keyring, mock_client):
        """Test --format json explicitly."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--format", "json",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # JSON format should have structured output
            assert "choices" in result.stdout


class TestQuietFlag:
    """Test --quiet flag."""

    def test_quiet_flag_recognized(self, mock_config, mock_keyring, mock_client):
        """Test --quiet flag is recognized."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--quiet",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

    def test_quiet_flag_short_form(self, mock_config, mock_keyring, mock_client):
        """Test -q short form of --quiet."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-q",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

    def test_quiet_flag_default_false(self, mock_config, mock_keyring, mock_client):
        """Test quiet flag defaults to False."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            # Without quiet flag, output should be normal
            assert len(result.stdout) > 0


class TestVerboseFlag:
    """Test --verbose flag."""

    def test_verbose_flag_recognized(self, mock_config, mock_keyring, mock_client):
        """Test --verbose flag is recognized."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--verbose",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

    def test_verbose_flag_debug_alias(self, mock_config, mock_keyring, mock_client):
        """Test --debug is alias for --verbose."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--debug",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0

    def test_verbose_flag_default_false(self, mock_config, mock_keyring, mock_client):
        """Test verbose flag defaults to False."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0


class TestShortFormOptions:
    """Test short form global options."""

    def test_profile_short_form_p_upper(self, mock_config, mock_keyring, mock_client):
        """Test -P short form for --profile."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-P", "prod-profile",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "prod-profile"

    def test_uri_short_form_u_upper(self, mock_config, mock_keyring, mock_client):
        """Test -U short form for --uri."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-U", "http://prod.example.com",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("uri") == "http://prod.example.com"

    def test_format_short_form_f(self, mock_config, mock_keyring, mock_client):
        """Test -f short form for --format."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-f", "json",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            assert "choices" in result.stdout

    def test_timeout_short_form_t(self, mock_config, mock_keyring, mock_client):
        """Test -t short form for --timeout."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-t", "30",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("timeout") == 30


class TestMultipleGlobalOptions:
    """Test multiple global options together."""

    def test_all_options_together(self, mock_config, mock_keyring, mock_client):
        """Test all global options together."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--profile", "test-profile",
                    "--uri", "http://test.local:9000",
                    "--token", "secret-token",
                    "--format", "json",
                    "--timeout", "45",
                    "--verbose",
                    "--quiet",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "test-profile"
            assert call_kwargs.get("uri") == "http://test.local:9000"
            assert call_kwargs.get("token") == "secret-token"
            assert call_kwargs.get("timeout") == 45

    def test_short_form_options_combined(self, mock_config, mock_keyring, mock_client):
        """Test short form options can be combined."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-P", "profile1",
                    "-U", "http://server1.com",
                    "-f", "json",
                    "-t", "50",
                    "-q",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "profile1"
            assert call_kwargs.get("uri") == "http://server1.com"
            assert call_kwargs.get("timeout") == 50

    def test_mixed_short_and_long_options(self, mock_config, mock_keyring, mock_client):
        """Test mixing short and long form options."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "-P", "profile2",
                    "--uri", "http://mixed.com",
                    "-f", "text",
                    "--token", "mixed-token",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "profile2"
            assert call_kwargs.get("uri") == "http://mixed.com"
            assert call_kwargs.get("token") == "mixed-token"


class TestGlobalOptionsWithDifferentCommands:
    """Test global options work with different subcommands."""

    def test_global_options_with_models_command(self, mock_config, mock_keyring):
        """Test global options are available for models command."""
        with patch("openwebui_cli.commands.models.create_client") as mock_create_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}
            mock_http_client.get.return_value = mock_response
            mock_create_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "--profile", "test-profile",
                    "--uri", "http://test.local",
                    "--token", "test-token",
                    "models", "list"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "test-profile"
            assert call_kwargs.get("uri") == "http://test.local"
            assert call_kwargs.get("token") == "test-token"

    def test_global_options_with_auth_command(self, mock_config, mock_keyring):
        """Test global options are available for auth command."""
        with patch("openwebui_cli.commands.auth.create_client") as mock_create_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"name": "test", "email": "test@example.com", "role": "user"}
            mock_http_client.get.return_value = mock_response
            mock_create_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "--profile", "auth-profile",
                    "--uri", "http://auth.local",
                    "auth", "whoami"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "auth-profile"
            assert call_kwargs.get("uri") == "http://auth.local"


class TestGlobalOptionsEdgeCases:
    """Test edge cases for global options."""

    def test_timeout_zero_value(self, mock_config, mock_keyring, mock_client):
        """Test timeout with zero value."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--timeout", "0",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("timeout") == 0

    def test_timeout_large_value(self, mock_config, mock_keyring, mock_client):
        """Test timeout with large value."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--timeout", "3600",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("timeout") == 3600

    def test_profile_with_special_characters(self, mock_config, mock_keyring, mock_client):
        """Test profile with special characters."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--profile", "test-profile_v2",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("profile") == "test-profile_v2"

    def test_uri_with_special_characters(self, mock_config, mock_keyring, mock_client):
        """Test URI with special characters and ports."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--uri", "http://test.example.com:9000/api",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("uri") == "http://test.example.com:9000/api"

    def test_token_with_special_characters(self, mock_config, mock_keyring, mock_client):
        """Test token with special characters."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            special_token = "sk-test_1234-5678$%&!@#"
            result = runner.invoke(
                app,
                [
                    "--token", special_token,
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            assert call_kwargs.get("token") == special_token

    def test_none_values_handled_correctly(self, mock_config, mock_keyring, mock_client):
        """Test that None values are handled correctly."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_create_client.call_args[1]
            # When not provided, these should be None
            assert call_kwargs.get("profile") is None
            assert call_kwargs.get("uri") is None
            assert call_kwargs.get("token") is None

    def test_format_with_unrecognized_value(self, mock_config, mock_keyring, mock_client):
        """Test format with unrecognized value (still stored, usage depends on command)."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            result = runner.invoke(
                app,
                [
                    "--format", "yaml",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            # Command succeeds; format validation is command-specific
            assert result.exit_code == 0


class TestGlobalOptionsContextIsolation:
    """Test that context is properly isolated between commands."""

    def test_context_not_shared_between_invocations(self, mock_config, mock_keyring, mock_client):
        """Test that context from one invocation doesn't leak to next."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_create_client:
            mock_create_client.return_value = mock_client

            # First invocation with profile1
            result1 = runner.invoke(
                app,
                [
                    "--profile", "profile1",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )
            assert result1.exit_code == 0

            # Second invocation with profile2
            result2 = runner.invoke(
                app,
                [
                    "--profile", "profile2",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )
            assert result2.exit_code == 0

            # Verify each invocation got the right profile
            calls = mock_create_client.call_args_list
            assert calls[0][1].get("profile") == "profile1"
            assert calls[1][1].get("profile") == "profile2"

    def test_context_persists_across_subcommand_calls(self, mock_config, mock_keyring):
        """Test that context persists when calling subcommands."""
        with patch("openwebui_cli.commands.chat.create_client") as mock_chat_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}}]
            }
            mock_http_client.post.return_value = mock_response
            mock_chat_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                [
                    "--token", "persistent-token",
                    "chat", "send",
                    "-m", "test-model",
                    "-p", "Hello",
                    "--no-stream"
                ],
            )

            assert result.exit_code == 0
            call_kwargs = mock_chat_client.call_args[1]
            assert call_kwargs.get("token") == "persistent-token"
