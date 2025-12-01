"""Tests for CLIError handling in main.py cli() function."""

import pytest
import typer
from io import StringIO
from unittest.mock import patch, MagicMock

from openwebui_cli.main import app, cli
from openwebui_cli.errors import CLIError, ExitCode, UsageError, AuthError, NetworkError, ServerError


class TestCLIErrorHandling:
    """Test that cli() function properly handles CLIError exceptions."""

    def test_clierror_with_custom_exit_code(self):
        """Test CLIError with custom exit code is properly propagated."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Test error", exit_code=5)

            # cli() catches CLIError and calls typer.Exit with the error code
            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 5

    def test_clierror_with_default_exit_code(self):
        """Test CLIError with default exit code (GENERAL_ERROR = 1)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Default error")

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == ExitCode.GENERAL_ERROR
            assert exc_info.value.exit_code == 1

    def test_clierror_exit_code_zero(self):
        """Test CLIError with exit code 0 is honored."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Success error", exit_code=0)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 0

    def test_clierror_exit_code_two(self):
        """Test CLIError with exit code 2 (USAGE_ERROR)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Usage error", exit_code=ExitCode.USAGE_ERROR)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 2

    def test_clierror_exit_code_three(self):
        """Test CLIError with exit code 3 (AUTH_ERROR)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Auth error", exit_code=ExitCode.AUTH_ERROR)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 3

    def test_clierror_exit_code_four(self):
        """Test CLIError with exit code 4 (NETWORK_ERROR)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Network error", exit_code=ExitCode.NETWORK_ERROR)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 4

    def test_clierror_exit_code_five(self):
        """Test CLIError with exit code 5 (SERVER_ERROR)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Server error", exit_code=ExitCode.SERVER_ERROR)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 5

    def test_usage_error_exit_code(self):
        """Test UsageError subclass propagates correct exit code."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = UsageError("Invalid arguments")

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == ExitCode.USAGE_ERROR
            assert exc_info.value.exit_code == 2

    def test_auth_error_exit_code(self):
        """Test AuthError subclass propagates correct exit code."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = AuthError("Authentication failed")

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == ExitCode.AUTH_ERROR
            assert exc_info.value.exit_code == 3

    def test_network_error_exit_code(self):
        """Test NetworkError subclass propagates correct exit code."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = NetworkError("Connection timeout")

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == ExitCode.NETWORK_ERROR
            assert exc_info.value.exit_code == 4

    def test_server_error_exit_code(self):
        """Test ServerError subclass propagates correct exit code."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = ServerError("Internal server error")

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == ExitCode.SERVER_ERROR
            assert exc_info.value.exit_code == 5

    def test_error_message_is_printed(self):
        """Test that error messages are printed to console."""
        with patch('openwebui_cli.main.app') as mock_app:
            with patch('openwebui_cli.main.console') as mock_console:
                error_message = "Test error message"
                mock_app.side_effect = CLIError(error_message, exit_code=1)

                with pytest.raises(typer.Exit) as exc_info:
                    cli()

                assert exc_info.value.exit_code == 1
                # Verify console.print was called with the error message
                mock_console.print.assert_called_once()
                call_args = mock_console.print.call_args[0][0]
                assert error_message in call_args or error_message in str(call_args)

    def test_multiple_clierror_scenarios(self):
        """Test various CLIError scenarios in sequence."""
        error_scenarios = [
            (CLIError("Error 1", exit_code=1), 1),
            (CLIError("Error 2", exit_code=2), 2),
            (AuthError("Auth failure"), 3),
            (NetworkError("Network issue"), 4),
            (ServerError("Server issue"), 5),
        ]

        for error, expected_code in error_scenarios:
            with patch('openwebui_cli.main.app') as mock_app:
                mock_app.side_effect = error

                with pytest.raises(typer.Exit) as exc_info:
                    cli()

                assert exc_info.value.exit_code == expected_code, \
                    f"Expected {expected_code} but got {exc_info.value.exit_code} for {error}"

    def test_clierror_large_exit_code(self):
        """Test CLIError with larger exit code values."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Large exit code error", exit_code=127)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 127

    def test_clierror_negative_exit_code(self):
        """Test CLIError with negative exit code (should still be respected)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Negative exit code", exit_code=-1)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            # typer.Exit will accept negative codes
            assert exc_info.value.exit_code == -1

    def test_clierror_empty_message(self):
        """Test CLIError with empty message."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("", exit_code=1)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 1

    def test_clierror_multiline_message(self):
        """Test CLIError with multiline message."""
        with patch('openwebui_cli.main.app') as mock_app:
            error_msg = "Line 1 of error\nLine 2 of error\nLine 3 of error"
            mock_app.side_effect = CLIError(error_msg, exit_code=1)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 1

    def test_clierror_with_special_characters(self):
        """Test CLIError message with special characters."""
        with patch('openwebui_cli.main.app') as mock_app:
            special_msg = "Error: $pecial ch@rs & symbols <>"
            mock_app.side_effect = CLIError(special_msg, exit_code=1)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 1

    def test_clierror_overrides_app_exit_code(self):
        """Test that CLIError exit code is used instead of app's exit code."""
        with patch('openwebui_cli.main.app') as mock_app:
            # Simulate app that would normally exit with different code
            mock_app.side_effect = CLIError("Overridden error", exit_code=42)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            # Should use CLIError's exit code, not any default
            assert exc_info.value.exit_code == 42

    def test_clierror_not_caught_by_other_handlers(self):
        """Test that non-CLIError exceptions are not caught by cli()."""
        with patch('openwebui_cli.main.app') as mock_app:
            # This should NOT be caught by cli()
            mock_app.side_effect = ValueError("Some other error")

            # cli() only catches CLIError, so this will raise ValueError
            with pytest.raises(ValueError, match="Some other error"):
                cli()

    def test_clierror_none_exit_code_uses_default(self):
        """Test that CLIError with None exit_code uses the class default."""
        with patch('openwebui_cli.main.app') as mock_app:
            # Create CLIError without specifying exit_code
            mock_app.side_effect = CLIError("Message without explicit code")

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            # Should default to GENERAL_ERROR = 1
            assert exc_info.value.exit_code == ExitCode.GENERAL_ERROR
            assert exc_info.value.exit_code == 1

    def test_clierror_with_console_output(self):
        """Test that error messages appear in console output."""
        with patch('openwebui_cli.main.app') as mock_app:
            with patch('openwebui_cli.main.console.print') as mock_print:
                error_msg = "Configuration Error: Invalid model specification"
                mock_app.side_effect = CLIError(error_msg, exit_code=2)

                with pytest.raises(typer.Exit) as exc_info:
                    cli()

                assert exc_info.value.exit_code == 2
                # Verify console.print was called
                assert mock_print.called


class TestCLIErrorIntegration:
    """Integration tests for CLIError handling with actual commands."""

    def test_clierror_caught_and_exit_code_applied(self):
        """Test that CLIError is caught and proper exit code is applied."""
        with patch('openwebui_cli.main.app') as mock_app:
            test_error = CLIError("Integration test error", exit_code=7)
            mock_app.side_effect = test_error

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 7

    def test_clierror_subclass_with_default_exit_code(self):
        """Test that CLIError subclasses use their class default exit code."""
        error_subclasses = [
            (UsageError("usage"), 2),
            (AuthError("auth"), 3),
            (NetworkError("network"), 4),
            (ServerError("server"), 5),
        ]

        for error_instance, expected_code in error_subclasses:
            with patch('openwebui_cli.main.app') as mock_app:
                mock_app.side_effect = error_instance

                with pytest.raises(typer.Exit) as exc_info:
                    cli()

                assert exc_info.value.exit_code == expected_code


class TestCLIErrorEdgeCases:
    """Test edge cases and boundary conditions for CLIError handling."""

    def test_clierror_with_unicode_characters(self):
        """Test CLIError with unicode characters."""
        with patch('openwebui_cli.main.app') as mock_app:
            unicode_msg = "Error: Database connection failed ✗ (timeout: 5000ms)"
            mock_app.side_effect = CLIError(unicode_msg, exit_code=1)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 1

    def test_clierror_exit_code_boundary_255(self):
        """Test CLIError with exit code 255 (max standard exit code)."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Max exit code", exit_code=255)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 255

    def test_clierror_exit_code_256(self):
        """Test CLIError with exit code beyond standard range."""
        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = CLIError("Beyond standard range", exit_code=256)

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            # typer.Exit allows values beyond standard range
            assert exc_info.value.exit_code == 256

    def test_clierror_with_exception_wrapping(self):
        """Test CLIError created from another exception."""
        with patch('openwebui_cli.main.app') as mock_app:
            original_error = ValueError("Original error")
            wrapped_error = CLIError(f"Wrapped: {str(original_error)}", exit_code=1)
            mock_app.side_effect = wrapped_error

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 1

    def test_clierror_different_subclass_exit_codes(self):
        """Test that each CLIError subclass maintains distinct exit codes."""
        error_classes = [
            (UsageError("usage"), ExitCode.USAGE_ERROR, 2),
            (AuthError("auth"), ExitCode.AUTH_ERROR, 3),
            (NetworkError("network"), ExitCode.NETWORK_ERROR, 4),
            (ServerError("server"), ExitCode.SERVER_ERROR, 5),
        ]

        for error, expected_exit_code_obj, expected_exit_code_int in error_classes:
            with patch('openwebui_cli.main.app') as mock_app:
                mock_app.side_effect = error

                with pytest.raises(typer.Exit) as exc_info:
                    cli()

                assert exc_info.value.exit_code == expected_exit_code_int
                assert error.exit_code == expected_exit_code_obj
                assert error.exit_code == expected_exit_code_int

    def test_clierror_instantiation_with_custom_exit_code(self):
        """Test CLIError instantiation correctly sets custom exit code."""
        error1 = CLIError("Error", exit_code=10)
        assert error1.exit_code == 10

        error2 = CLIError("Error without code")
        assert error2.exit_code == ExitCode.GENERAL_ERROR

    def test_clierror_subclass_instantiation_with_override(self):
        """Test CLIError subclass with overridden exit code."""
        # UsageError normally has exit_code = 2
        # But can be overridden
        error = UsageError("Custom usage error", exit_code=99)
        assert error.exit_code == 99

        with patch('openwebui_cli.main.app') as mock_app:
            mock_app.side_effect = error

            with pytest.raises(typer.Exit) as exc_info:
                cli()

            assert exc_info.value.exit_code == 99
