"""HTTP client wrapper for OpenWebUI API."""

from typing import Any

import httpx
import keyring

from .config import get_effective_config, load_config
from .errors import AuthError, NetworkError, ServerError

KEYRING_SERVICE = "openwebui-cli"


def get_token(profile: str, uri: str) -> str | None:
    """Retrieve token from system keyring."""
    key = f"{profile}:{uri}"
    return keyring.get_password(KEYRING_SERVICE, key)


def set_token(profile: str, uri: str, token: str) -> None:
    """Store token in system keyring."""
    key = f"{profile}:{uri}"
    keyring.set_password(KEYRING_SERVICE, key, token)


def delete_token(profile: str, uri: str) -> None:
    """Delete token from system keyring."""
    key = f"{profile}:{uri}"
    try:
        keyring.delete_password(KEYRING_SERVICE, key)
    except keyring.errors.PasswordDeleteError:
        pass  # Token doesn't exist, that's fine


def create_client(
    profile: str | None = None,
    uri: str | None = None,
    token: str | None = None,
    timeout: float | None = None,
) -> httpx.Client:
    """
    Create an HTTP client configured for OpenWebUI API.

    Args:
        profile: Profile name to use
        uri: Override server URI
        token: Override token (otherwise uses env var or keyring)
        timeout: Request timeout in seconds

    Returns:
        Configured httpx.Client
    """
    effective_uri, effective_profile = get_effective_config(profile, uri)
    config = load_config()

    # Get token with precedence: param > env var > keyring
    if token is None:
        from .config import Settings

        settings = Settings()
        token = settings.openwebui_token or get_token(effective_profile, effective_uri)

    # Build headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Use config timeout if not specified
    if timeout is None:
        timeout = config.defaults.timeout

    return httpx.Client(
        base_url=effective_uri,
        headers=headers,
        timeout=timeout,
    )


def create_async_client(
    profile: str | None = None,
    uri: str | None = None,
    token: str | None = None,
    timeout: float | None = None,
) -> httpx.AsyncClient:
    """Create an async HTTP client configured for OpenWebUI API."""
    effective_uri, effective_profile = get_effective_config(profile, uri)
    config = load_config()

    # Get token with precedence: param > env var > keyring
    if token is None:
        from .config import Settings

        settings = Settings()
        token = settings.openwebui_token or get_token(effective_profile, effective_uri)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if timeout is None:
        timeout = config.defaults.timeout

    return httpx.AsyncClient(
        base_url=effective_uri,
        headers=headers,
        timeout=timeout,
    )


def handle_response(response: httpx.Response) -> dict[str, Any]:
    """
    Handle API response, raising appropriate errors for failures.

    Returns:
        Parsed JSON response

    Raises:
        AuthError: For 401/403 responses
        ServerError: For 5xx responses
        CLIError: For other error responses
    """
    if response.status_code == 401:
        raise AuthError(
            "Authentication required. Please run 'openwebui auth login' first.\n"
            "If you recently logged in, your token may have expired."
        )
    elif response.status_code == 403:
        raise AuthError(
            "Permission denied. This operation requires higher privileges.\n"
            "Possible causes:\n"
            "  - Your user role lacks required permissions\n"
            "  - The API key doesn't have sufficient access\n"
            "  - Try logging in again: openwebui auth login"
        )
    elif response.status_code == 404:
        try:
            error_data = response.json()
            message = error_data.get("detail", error_data.get("message", "Resource not found"))
        except Exception:
            message = "Resource not found"
        raise ServerError(
            f"Not found: {message}\nCheck that the resource ID, model name, or endpoint is correct."
        )
    elif response.status_code >= 500:
        raise ServerError(
            f"Server error ({response.status_code}): {response.text}\n"
            "The OpenWebUI server encountered an error.\n"
            "Try again in a moment, or check server logs if you're the administrator."
        )
    elif response.status_code >= 400:
        try:
            error_data = response.json()
            message = error_data.get("detail", error_data.get("message", response.text))
        except Exception:
            message = response.text
        raise ServerError(
            f"API error ({response.status_code}): {message}\n"
            "Check your request parameters and try again."
        )

    try:
        return response.json()
    except Exception:
        return {"text": response.text}


def handle_request_error(error: Exception) -> None:
    """Convert httpx errors to CLI errors."""
    if isinstance(error, httpx.ConnectError):
        raise NetworkError(
            f"Could not connect to server: {error}\n"
            "Possible solutions:\n"
            "  - Check that OpenWebUI is running\n"
            "  - Verify the URI: openwebui config init\n"
            "  - Try: openwebui --uri http://localhost:8080 auth login"
        )
    elif isinstance(error, httpx.TimeoutException):
        raise NetworkError(
            f"Request timed out: {error}\n"
            "Possible solutions:\n"
            "  - Increase timeout: openwebui --timeout 60 ...\n"
            "  - Check your network connection\n"
            "  - The server might be overloaded"
        )
    elif isinstance(error, httpx.RequestError):
        raise NetworkError(
            f"Request failed: {error}\nCheck your network connection and server configuration."
        )
    else:
        raise error
