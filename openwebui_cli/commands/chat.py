"""Chat commands."""

import json
import sys

import typer
from rich.console import Console
from rich.live import Live
from rich.text import Text

from ..config import load_config
from ..http import create_client, handle_response, handle_request_error

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def send(
    ctx: typer.Context,
    model: str = typer.Option(..., "--model", "-m", help="Model to use"),
    prompt: str | None = typer.Option(None, "--prompt", "-p", help="User prompt (or use stdin)"),
    system: str | None = typer.Option(None, "--system", "-s", help="System prompt"),
    chat_id: str | None = typer.Option(None, "--chat-id", help="Continue existing conversation"),
    file: list[str] | None = typer.Option(None, "--file", help="RAG file ID(s) for context"),
    collection: list[str] | None = typer.Option(None, "--collection", help="RAG collection ID(s) for context"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Wait for complete response"),
    temperature: float | None = typer.Option(None, "--temperature", "-T", help="Temperature (0.0-2.0)"),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Max response tokens"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Send a chat message."""
    obj = ctx.obj or {}
    config = load_config()

    # Get prompt from stdin if not provided
    if prompt is None:
        if not sys.stdin.isatty():
            prompt = sys.stdin.read().strip()
        else:
            console.print("[red]Error: Prompt required. Use -p or pipe input.[/red]")
            raise typer.Exit(2)

    # Build messages
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Build request body
    body: dict = {
        "model": model,
        "messages": messages,
        "stream": not no_stream and config.defaults.stream,
    }

    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens

    # Add RAG context if specified
    files_context = []
    if file:
        for f in file:
            files_context.append({"type": "file", "id": f})
    if collection:
        for c in collection:
            files_context.append({"type": "collection", "id": c})
    if files_context:
        body["files"] = files_context

    try:
        with create_client(
            profile=obj.get("profile"),
            uri=obj.get("uri"),
            timeout=obj.get("timeout"),
        ) as client:
            if body.get("stream"):
                # Streaming response
                with client.stream(
                    "POST",
                    "/api/v1/chat/completions",
                    json=body,
                ) as response:
                    if response.status_code >= 400:
                        handle_response(response)

                    full_content = ""
                    for line in response.iter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    print(content, end="", flush=True)
                                    full_content += content
                            except json.JSONDecodeError:
                                continue
                    print()  # Final newline

                    if json_output:
                        console.print(json.dumps({"content": full_content}, indent=2))
            else:
                # Non-streaming response
                response = client.post("/api/v1/chat/completions", json=body)
                data = handle_response(response)

                if json_output or obj.get("format") == "json":
                    console.print(json.dumps(data, indent=2))
                else:
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    console.print(content)

    except Exception as e:
        handle_request_error(e)


@app.command("list")
def list_chats(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-n", help="Number of chats to show"),
    archived: bool = typer.Option(False, "--archived", help="Show archived chats"),
) -> None:
    """List conversations (v1.1 feature - placeholder)."""
    console.print("[yellow]Chat list will be available in v1.1[/yellow]")


@app.command()
def show(
    ctx: typer.Context,
    chat_id: str = typer.Argument(..., help="Chat ID to show"),
) -> None:
    """Show conversation details (v1.1 feature - placeholder)."""
    console.print("[yellow]Chat show will be available in v1.1[/yellow]")


@app.command()
def export(
    ctx: typer.Context,
    chat_id: str = typer.Argument(..., help="Chat ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, markdown"),
) -> None:
    """Export conversation (v1.1 feature - placeholder)."""
    console.print("[yellow]Chat export will be available in v1.1[/yellow]")
