"""Tests for error handling."""

import pytest

from openwebui_cli.errors import (
    AuthError,
    CLIError,
    ExitCode,
    NetworkError,
    ServerError,
    UsageError,
    handle_error,
)


def test_exit_codes():
    """Test exit code values."""
    assert ExitCode.SUCCESS == 0
    assert ExitCode.GENERAL_ERROR == 1
    assert ExitCode.USAGE_ERROR == 2
    assert ExitCode.AUTH_ERROR == 3
    assert ExitCode.NETWORK_ERROR == 4
    assert ExitCode.SERVER_ERROR == 5


def test_cli_error():
    """Test base CLI error."""
    error = CLIError("Test error")
    assert str(error) == "Test error"
    assert error.exit_code == ExitCode.GENERAL_ERROR


def test_error_classes():
    """Test specific error classes have correct exit codes."""
    assert UsageError("test").exit_code == ExitCode.USAGE_ERROR
    assert AuthError("test").exit_code == ExitCode.AUTH_ERROR
    assert NetworkError("test").exit_code == ExitCode.NETWORK_ERROR
    assert ServerError("test").exit_code == ExitCode.SERVER_ERROR


def test_handle_error():
    """Test error handling returns correct exit codes."""
    assert handle_error(UsageError("test")) == ExitCode.USAGE_ERROR
    assert handle_error(AuthError("test")) == ExitCode.AUTH_ERROR
    assert handle_error(NetworkError("test")) == ExitCode.NETWORK_ERROR
    assert handle_error(ServerError("test")) == ExitCode.SERVER_ERROR
    assert handle_error(Exception("test")) == ExitCode.GENERAL_ERROR
