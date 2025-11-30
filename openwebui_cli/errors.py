"""CLI error classes with standardized exit codes."""

import sys
from enum import IntEnum


class ExitCode(IntEnum):
    """Standardized exit codes for the CLI."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    USAGE_ERROR = 2
    AUTH_ERROR = 3
    NETWORK_ERROR = 4
    SERVER_ERROR = 5


class CLIError(Exception):
    """Base exception for CLI errors."""

    exit_code: int = ExitCode.GENERAL_ERROR

    def __init__(self, message: str, exit_code: int | None = None):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class UsageError(CLIError):
    """Invalid command usage or arguments."""

    exit_code = ExitCode.USAGE_ERROR


class AuthError(CLIError):
    """Authentication or authorization failure."""

    exit_code = ExitCode.AUTH_ERROR


class NetworkError(CLIError):
    """Network connectivity or timeout error."""

    exit_code = ExitCode.NETWORK_ERROR


class ServerError(CLIError):
    """Server returned an error (5xx)."""

    exit_code = ExitCode.SERVER_ERROR


def handle_error(error: Exception) -> int:
    """Handle an error and return the appropriate exit code."""
    if isinstance(error, CLIError):
        print(f"Error: {error}", file=sys.stderr)
        return error.exit_code
    else:
        print(f"Unexpected error: {error}", file=sys.stderr)
        return ExitCode.GENERAL_ERROR
