"""HTTP client wrapper for OpenWebUI API."""

from typing import Any

import httpx
import keyring
from rich.console import Console

from .config import get_effective_config, load_config
from .errors import AuthError, NetworkError, ServerError

KEYRING_SERVICE = "openwebui-cli"


def get_token(profile: str, uri: str) -> str | None:
    """Retrieve token from system keyring."""
    key = f"{profile}:{uri}"
    try:
        return keyring.get_password(KEYRING_SERVICE, key)
    except keyring.errors.KeyringError:
        # No keyring backend available; allow caller to fall back to env/CLI token.
        return None


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
    allow_unauthenticated: bool = False,
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

    # Get token with precedence: CLI param > env var > keyring
    if token is None:
        from .config import Settings

        settings = Settings()
        token = settings.openwebui_token
        if token is None:
            try:
                token = get_token(effective_profile, effective_uri)
            except keyring.errors.KeyringError as e:
                raise AuthError(
                    "No keyring backend available.\n"
                    "Set OPENWEBUI_TOKEN or pass --token to use the CLI without keyring, "
                    "or install a keyring backend (e.g., pip install keyrings.alt)."
                ) from e

    if token is None:
        if allow_unauthenticated:
            token = None
        else:
            raise AuthError(
                "No authentication token available.\n"
                "Log in with 'openwebui auth login' or provide a token via:\n"
                "  - env: OPENWEBUI_TOKEN\n"
                "  - CLI: --token <TOKEN>\n"
                "If using keyring, install a backend (e.g., keyrings.alt)."
            )

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
    allow_unauthenticated: bool = False,
) -> httpx.AsyncClient:
    """Create an async HTTP client configured for OpenWebUI API."""
    effective_uri, effective_profile = get_effective_config(profile, uri)
    config = load_config()

    # Get token with precedence: CLI param > env var > keyring
    if token is None:
        from .config import Settings

        settings = Settings()
        token = settings.openwebui_token
        if token is None:
            try:
                token = get_token(effective_profile, effective_uri)
            except keyring.errors.KeyringError as e:
                raise AuthError(
                    "No keyring backend available.\n"
                    "Set OPENWEBUI_TOKEN or pass --token to use the CLI without keyring, "
                    "or install a keyring backend (e.g., pip install keyrings.alt)."
                ) from e

    if token is None:
        if not allow_unauthenticated:
            raise AuthError(
                "No authentication token available.\n"
                "Log in with 'openwebui auth login' or provide a token via:\n"
                "  - env: OPENWEBUI_TOKEN\n"
                "  - CLI: --token <TOKEN>\n"
                "If using keyring, install a backend (e.g., keyrings.alt)."
            )

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
        data: dict[str, Any] = response.json()
        return data
    except Exception:
        return {"text": response.text}


def handle_request_error(error: Exception) -> None:
    """Convert httpx errors to CLI errors."""
    if isinstance(error, keyring.errors.KeyringError):
        raise AuthError(
            "Keyring is unavailable.\n"
            "Install a backend (e.g., pip install keyrings.alt) or provide a token via "
            "OPENWEBUI_TOKEN / --token."
        )
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
        url_msg = ""
        try:
            request_url = error.request.url  # may raise if request is unset
            url_msg = f" (URL: {request_url!s})"
        except Exception:
            url_msg = ""
        verbose_note = " Use --verbose for details." if _is_verbose_enabled() else ""
        raise NetworkError(
            f"Request failed: {error}{url_msg}\n"
            f"Check your network connection and server configuration.{verbose_note}"
        )
    else:
        # Bubble up unknown errors unchanged (e.g., typer.Exit for graceful exits)
        raise error


def _is_verbose_enabled() -> bool:
    """Return True if the current Typer context has verbose/debug enabled."""
    try:
        import typer

        ctx = typer.get_current_context(silent=True)
        if ctx and isinstance(ctx.obj, dict):
            return bool(ctx.obj.get("verbose"))
    except Exception:
        return False
    return False
