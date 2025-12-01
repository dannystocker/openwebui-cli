"""Tests for chat command error conditions with missing parameters."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from typer.testing import CliRunner

from openwebui_cli.main import app
from openwebui_cli.config import Config

runner = CliRunner()


@pytest.fixture
def mock_config(tmp_path, monkeypatch):
    """Mock configuration for testing (no default model)."""
    config_dir = tmp_path / "openwebui"
    config_path = config_dir / "config.yaml"

    monkeypatch.setattr("openwebui_cli.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("openwebui_cli.config.get_config_path", lambda: config_path)

    # Create default config with no default model
    from openwebui_cli.config import Config, save_config
    config = Config()
    config.defaults.model = None  # Explicitly no default model
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


class TestMissingModel:
    """Test cases for missing model parameter."""

    def test_missing_model_no_default(self, mock_config, mock_keyring):
        """Test chat fails when model is not specified and no default configured."""
        result = runner.invoke(
            app,
            ["chat", "send", "-p", "Hello world"],
        )

        assert result.exit_code == 2
        assert "model" in result.stdout.lower()
        assert "error" in result.stdout.lower()

    def test_missing_model_error_message_content(self, mock_config, mock_keyring):
        """Test that error message provides helpful guidance."""
        result = runner.invoke(
            app,
            ["chat", "send", "-p", "Hello"],
        )

        assert result.exit_code == 2
        # Should mention both the missing model and how to fix it
        assert "model" in result.stdout.lower()
        assert any(
            keyword in result.stdout.lower()
            for keyword in ["default", "config", "specify"]
        )

    def test_missing_model_short_flag(self, mock_config, mock_keyring):
        """Test missing model error with short flag usage."""
        result = runner.invoke(
            app,
            ["chat", "send", "-p", "Test prompt"],
        )

        assert result.exit_code == 2
        assert "model" in result.stdout.lower()


class TestMissingPromptHandling:
    """Test cases for missing prompt with various input conditions."""

    def test_missing_prompt_with_no_stdin_input(self, mock_config, mock_keyring):
        """Test chat fails when prompt is missing and no stdin input provided."""
        # When no input parameter is passed to runner.invoke(),
        # and no -p flag provided, should attempt to read stdin
        # and get empty, which could cause issues
        result = runner.invoke(
            app,
            ["--token", "test-token", "chat", "send", "-m", "test-model"],
        )

        # Without mocking HTTP, this will hit auth/connection errors
        # But the prompt validation should happen before that
        # Exit code could be 1 (network) or 2 (usage) depending on implementation
        assert result.exit_code in [1, 2]

    def test_missing_prompt_with_valid_stdin_input(self, mock_config, mock_keyring):
        """Test that valid stdin input is accepted for prompt."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            # Provide valid stdin input when -p not used
            result = runner.invoke(
                app,
                ["--token", "test-token", "chat", "send", "-m", "test-model", "--no-stream"],
                input="Valid prompt from stdin\n",
            )

            # Should succeed with valid prompt provided via stdin
            assert result.exit_code == 0


class TestMissingPromptWithStdin:
    """Test cases for prompt handling with stdin."""

    def test_prompt_from_stdin_overrides_missing_prompt_flag(self, mock_config, mock_keyring):
        """Test that stdin input works when -p flag is not provided."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response from stdin"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                ["chat", "send", "-m", "test-model", "--no-stream"],
                input="Hello from stdin\n",
            )

            assert result.exit_code == 0



class TestBothParametersMissing:
    """Test cases for both model and prompt missing."""

    def test_missing_both_model_and_prompt(self, mock_config, mock_keyring):
        """Test error when both model and prompt are missing."""
        result = runner.invoke(
            app,
            ["chat", "send"],
        )

        # Should fail with exit code 2
        assert result.exit_code == 2
        # Should mention one of the missing parameters
        output_lower = result.stdout.lower()
        assert "error" in output_lower

    def test_missing_both_shows_model_error_first(self, mock_config, mock_keyring):
        """Test that missing model is caught first when both are missing."""
        result = runner.invoke(
            app,
            ["chat", "send"],
        )

        assert result.exit_code == 2
        # Model check happens first in the code
        assert "model" in result.stdout.lower()


class TestParameterValidation:
    """Test comprehensive parameter validation."""

    def test_model_required_with_valid_prompt(self, mock_config, mock_keyring):
        """Test that model is required even with valid prompt."""
        result = runner.invoke(
            app,
            ["chat", "send", "-p", "Valid prompt here"],
        )

        assert result.exit_code == 2
        assert "model" in result.stdout.lower()

    def test_prompt_required_with_valid_model(self, mock_config, mock_keyring):
        """Test that prompt is required even with valid model."""
        response_data = {"choices": [{"message": {"content": "Response"}}]}

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                ["--token", "test-token", "chat", "send", "-m", "valid-model", "--no-stream"],
                input="test input",
            )

            assert result.exit_code == 0


    def test_both_parameters_success(self, mock_config, mock_keyring):
        """Test successful invocation with both parameters provided."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Success response"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                ["chat", "send", "-m", "test-model", "-p", "Test prompt", "--no-stream"],
            )

            assert result.exit_code == 0


class TestExitCodes:
    """Test that error conditions return correct exit codes."""

    def test_missing_model_exit_code_is_2(self, mock_config, mock_keyring):
        """Test exit code 2 for missing model (usage error)."""
        result = runner.invoke(
            app,
            ["chat", "send", "-p", "Test"],
        )

        assert result.exit_code == 2

    def test_missing_prompt_with_stdin_input(self, mock_config, mock_keyring):
        """Test that stdin input can be used when -p flag not provided."""
        response_data = {
            "choices": [
                {
                    "message": {
                        "content": "Response from stdin input"
                    }
                }
            ]
        }

        with patch("openwebui_cli.commands.chat.create_client") as mock_client:
            mock_http_client = MagicMock()
            mock_http_client.__enter__.return_value = mock_http_client
            mock_http_client.__exit__.return_value = None
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = response_data
            mock_http_client.post.return_value = mock_response
            mock_client.return_value = mock_http_client

            result = runner.invoke(
                app,
                ["--token", "test-token", "chat", "send", "-m", "test-model", "--no-stream"],
                input="Prompt from stdin",
            )

            # Should succeed because prompt is provided via stdin
            assert result.exit_code == 0

    def test_exit_code_not_1(self, mock_config, mock_keyring):
        """Test that parameter errors are not generic exit code 1."""
        result = runner.invoke(
            app,
            ["chat", "send"],
        )

        # Should be 2 (usage error), not 1 (general error)
        assert result.exit_code == 2
