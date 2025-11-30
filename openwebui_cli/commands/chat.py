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
    history_file: str | None = typer.Option(None, "--history-file", help="Load conversation history from JSON file"),
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

    # Load conversation history if provided
    messages = []
    if history_file:
        try:
            from pathlib import Path
            history_path = Path(history_file)
            if not history_path.exists():
                console.print(f"[red]Error: History file not found: {history_file}[/red]")
                raise typer.Exit(2)

            with open(history_path) as f:
                history_data = json.load(f)
                # Support both direct array and object with 'messages' key
                if isinstance(history_data, list):
                    messages = history_data
                elif isinstance(history_data, dict) and "messages" in history_data:
                    messages = history_data["messages"]
                else:
                    console.print("[red]Error: History file must contain array of messages or object with 'messages' key[/red]")
                    raise typer.Exit(2)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON in history file: {e}[/red]")
            raise typer.Exit(2)
        except Exception as e:
            console.print(f"[red]Error loading history file: {e}[/red]")
            raise typer.Exit(2)

    # Build messages (add system prompt if not in history)
    if system and not any(msg.get("role") == "system" for msg in messages):
        messages.insert(0, {"role": "system", "content": system})

    # Add current user prompt
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
                try:
                    with client.stream(
                        "POST",
                        "/api/v1/chat/completions",
                        json=body,
                    ) as response:
                        if response.status_code >= 400:
                            handle_response(response)

                        full_content = ""
                        try:
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
                                        # Skip malformed JSON chunks
                                        continue
                        except KeyboardInterrupt:
                            # Gracefully handle Ctrl-C during streaming
                            print()  # Newline after partial output
                            console.print("\n[yellow]Stream interrupted by user[/yellow]")
                            if full_content and json_output:
                                console.print(json.dumps({"content": full_content, "interrupted": True}, indent=2))
                            raise typer.Exit(0)

                        print()  # Final newline

                        if json_output:
                            console.print(json.dumps({"content": full_content}, indent=2))

                except (ConnectionError, TimeoutError) as e:
                    console.print(f"\n[red]Connection error during streaming: {e}[/red]")
                    console.print("[yellow]Try reducing timeout or checking network connection[/yellow]")
                    raise typer.Exit(4)
            else:
                # Non-streaming response
                response = client.post("/api/v1/chat/completions", json=body)
                data = handle_response(response)

                if json_output or obj.get("format") == "json":
                    console.print(json.dumps(data, indent=2))
                else:
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    console.print(content)

    except KeyboardInterrupt:
        # Handle Ctrl-C at top level
        console.print("\n[yellow]Operation cancelled[/yellow]")
        raise typer.Exit(0)
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
