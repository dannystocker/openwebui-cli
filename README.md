# OpenWebUI CLI

Official command-line interface for [OpenWebUI](https://github.com/open-webui/open-webui).

> **Status:** Alpha - v0.1.0 MVP in development

## Features

- **Authentication** - Login, logout, token management with secure keyring storage
- **Chat** - Send messages with streaming support, continue conversations
- **RAG** - Upload files, manage collections, vector search
- **Models** - List and inspect available models
- **Admin** - Server stats and diagnostics (admin role required)
- **Profiles** - Multiple server configurations

## Installation

```bash
pip install openwebui-cli
```

Or from source:

```bash
git clone https://github.com/dannystocker/openwebui-cli.git
cd openwebui-cli
pip install -e .
```

## Quick Start

```bash
# Initialize configuration
openwebui config init

# Login to your OpenWebUI instance
openwebui auth login

# Chat with a model
openwebui chat send -m llama3.2:latest -p "Hello, world!"

# Upload a file for RAG
openwebui rag files upload ./document.pdf

# List available models
openwebui models list
```

## Usage

### Authentication

```bash
# Interactive login
openwebui auth login

# Show current user
openwebui auth whoami

# Logout
openwebui auth logout
```

### Chat

```bash
# Simple chat (streaming by default)
openwebui chat send -m llama3.2:latest -p "Explain quantum computing"

# Non-streaming mode
openwebui chat send -m llama3.2:latest -p "Hello" --no-stream

# With RAG context
openwebui chat send -m llama3.2:latest -p "Summarize this document" --file <FILE_ID>

# Continue a conversation
openwebui chat send -m llama3.2:latest -p "Tell me more" --chat-id <CHAT_ID>
```

### RAG (Retrieval-Augmented Generation)

```bash
# Upload files
openwebui rag files upload ./docs/*.pdf

# Create a collection
openwebui rag collections create "Project Docs"

# Search within a collection
openwebui rag search "authentication flow" --collection <COLL_ID>
```

### Models

```bash
# List all models
openwebui models list

# Get model details
openwebui models info llama3.2:latest
```

### Configuration

```bash
# Initialize config
openwebui config init

# Show current config
openwebui config show

# Use a specific profile
openwebui --profile production chat send -m gpt-4 -p "Hello"
```

## Configuration File

Location: `~/.config/openwebui/config.yaml` (Linux/macOS) or `%APPDATA%\openwebui\config.yaml` (Windows)

```yaml
version: 1
default_profile: local

profiles:
  local:
    uri: http://localhost:8080
  production:
    uri: https://openwebui.example.com

defaults:
  model: llama3.2:latest
  format: text
  stream: true
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Usage/argument error |
| 3 | Authentication error |
| 4 | Network error |
| 5 | Server error (5xx) |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy openwebui_cli

# Linting
ruff check openwebui_cli
```

## Contributing

Contributions welcome! Please read the [RFC proposal](docs/RFC.md) for design details.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [OpenWebUI](https://github.com/open-webui/open-webui) team
- [mitchty/open-webui-cli](https://github.com/mitchty/open-webui-cli) for inspiration
