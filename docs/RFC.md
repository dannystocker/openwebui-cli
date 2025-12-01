# OpenWebUI Official CLI - RFC Proposal

**Document Version:** 1.2
**Date:** November 30, 2025
**Author:** InfraFabric Team
**Target:** OpenWebUI Core Team Review
**Status:** DRAFT - Reviewed & Implementation-Ready

---

## Executive Summary

We propose building an **official CLI for OpenWebUI** to complement the web interface. This CLI would enable developers, DevOps engineers, and power users to interact with OpenWebUI programmatically from the command line, enabling automation, scripting, and integration into CI/CD pipelines.

**Why Now:**
- No official CLI exists (only `open-webui serve` to start server)
- Community demand evidenced by third-party CLI projects
- API surface is mature and well-documented
- Enables new use cases: automation, headless operation, batch processing

---

## Resources Available for Development

### ChromaDB Knowledge Base (Proxmox Server)

We have ingested the **entire OpenWebUI ecosystem** into a semantic search database:

| Collection | Documents | Content |
|------------|-----------|---------|
| `openwebui_core` | 8,014 | Full source code (backend + frontend) |
| `openwebui_docs` | 1,005 | Official documentation |
| `openwebui_functions` | 315 | Functions repository |
| `openwebui_pipelines` | 274 | Pipelines repository |
| `openwebui_pain_points` | 219 | GitHub issues (bug reports, feature requests) |
| `openwebui_careers` | 4 | Team/culture context |
| **TOTAL** | **9,832 chunks** | Complete ecosystem knowledge |

**Query Example:**
```python
import chromadb
c = chromadb.PersistentClient('/root/openwebui-knowledge/chromadb')
results = c.get_collection('openwebui_core').query(
    query_texts=['API endpoint authentication'],
    n_results=10
)
```

This knowledge base allows us to:
- Understand all API endpoints and their parameters
- Identify user pain points from GitHub issues
- Follow existing code patterns and conventions
- Ensure compatibility with current architecture

### Discovered API Surface (from source analysis)

**Router Files Found:**
- `auths.py` - Authentication, tokens, API keys
- `models.py` - Model management
- `ollama.py` - Ollama integration
- `functions.py` - Custom functions
- `pipelines.py` - Pipeline management
- `evaluations.py` - Model evaluations
- `scim.py` - SCIM provisioning

**Key Endpoints Identified:**
```
POST /api/v1/chat/completions     - Main chat endpoint (OpenAI-compatible)
POST /v1/chat/completions         - Ollama passthrough
POST /api/v1/tasks/*/completions  - Various task endpoints
GET  /api/models                  - List models
POST /api/pull                    - Pull model
POST /rag/upload                  - Upload RAG file
GET  /api/v1/knowledge            - List collections
```

### Pain Points from GitHub Issues

| Issue | Problem | CLI Solution |
|-------|---------|--------------|
| #19420 | Unable to create API keys - 403 | `openwebui auth keys create` with proper scopes |
| #19401 | Redis Sentinel auth bug | Config profiles with full connection strings |
| #19403 | API keys refactor needed | First-class API key management in CLI |
| #18948 | OAuth/OIDC complexity | `openwebui auth login --oauth` flow |
| #19131 | OIDC client_id issues | Proper OAuth parameter handling |

### Existing Third-Party CLI Analysis

**mitchty/open-webui-cli** (Rust):
- 40 commits, actively maintained (v0.1.2, Nov 2024)
- ~1000 lines of Rust code
- Features: chat, models, RAG collections, file upload

**What Works:**
- Bearer token authentication
- Collection/file-based RAG queries
- Model list/pull operations
- Clean command structure

**What's Missing:**
- No streaming support
- No OAuth flow
- No config file (env vars only)
- No admin operations
- No function/pipeline management
- Rust = different stack than OpenWebUI (Python)

---

## Proposed CLI Architecture

### Command Structure

```
openwebui [global-options] <command> <subcommand> [options]

Global Options:
  --uri <URL>           Server URL (default: $OPENWEBUI_URI or http://localhost:8080)
  --token <TOKEN>       API token (default: $OPENWEBUI_TOKEN)
  --profile <NAME>      Use named profile from config
  --format <FORMAT>     Output format: text, json, yaml (default: text)
  --quiet               Suppress non-essential output
  --verbose             Enable debug logging
  --version             Show version
  --help                Show help
```

### Complete Command Tree

```
openwebui
│
├── auth                          # Authentication & Authorization
│   ├── login                     # Interactive login (user/pass or OAuth)
│   │   ├── --username, -u        # Username for basic auth
│   │   ├── --password, -p        # Password (prompt if not provided)
│   │   ├── --oauth               # Use OAuth/OIDC flow
│   │   └── --provider <NAME>     # OAuth provider name
│   ├── logout                    # Revoke current token
│   ├── token                     # Show current token info
│   │   ├── --refresh             # Refresh token
│   │   └── --export              # Export token for scripts
│   ├── keys                      # API key management
│   │   ├── list                  # List API keys
│   │   ├── create <NAME>         # Create new API key
│   │   │   └── --scopes <LIST>   # Comma-separated scopes
│   │   ├── revoke <KEY_ID>       # Revoke API key
│   │   └── info <KEY_ID>         # Show key details
│   └── whoami                    # Show current user info
│
├── chat                          # Chat Operations
│   ├── send                      # Send a message
│   │   ├── --model, -m <MODEL>   # Model to use (required)
│   │   ├── --prompt, -p <TEXT>   # User prompt (or stdin)
│   │   ├── --system, -s <TEXT>   # System prompt
│   │   ├── --file <ID>           # RAG file ID(s) for context
│   │   ├── --collection <ID>     # RAG collection ID(s) for context
│   │   ├── --stream              # Stream response (default: true)
│   │   ├── --no-stream           # Wait for complete response
│   │   ├── --chat-id <ID>        # Continue existing conversation
│   │   ├── --temperature <FLOAT> # Temperature (0.0-2.0)
│   │   ├── --max-tokens <INT>    # Max response tokens
│   │   └── --json                # Request JSON output
│   ├── list                      # List conversations
│   │   ├── --limit <N>           # Number to show (default: 20)
│   │   ├── --archived            # Show archived chats
│   │   └── --search <QUERY>      # Search conversations
│   ├── show <CHAT_ID>            # Show conversation details
│   ├── export <CHAT_ID>          # Export conversation
│   │   └── --format <FMT>        # json, markdown, txt
│   ├── archive <CHAT_ID>         # Archive conversation
│   ├── unarchive <CHAT_ID>       # Unarchive conversation
│   └── delete <CHAT_ID>          # Delete conversation
│
├── models                        # Model Management
│   ├── list                      # List available models
│   │   ├── --provider <NAME>     # Filter by provider (ollama, openai, etc.)
│   │   └── --capabilities        # Show model capabilities
│   ├── info <MODEL_ID>           # Show model details
│   ├── pull <MODEL_NAME>         # Pull/download model (Ollama)
│   │   └── --progress            # Show download progress
│   ├── delete <MODEL_NAME>       # Delete model
│   └── copy <SRC> <DST>          # Copy/alias model
│
├── rag                           # RAG (Retrieval-Augmented Generation)
│   ├── files                     # File operations
│   │   ├── list                  # List uploaded files
│   │   ├── upload <PATH>...      # Upload file(s)
│   │   │   ├── --collection <ID> # Add to collection
│   │   │   └── --tags <LIST>     # Add tags
│   │   ├── info <FILE_ID>        # File details
│   │   ├── download <FILE_ID>    # Download file
│   │   └── delete <FILE_ID>      # Delete file
│   ├── collections               # Collection operations
│   │   ├── list                  # List collections
│   │   ├── create <NAME>         # Create collection
│   │   │   └── --description <TEXT>
│   │   ├── info <COLL_ID>        # Collection details
│   │   ├── add <COLL_ID> <FILE_ID>... # Add files to collection
│   │   ├── remove <COLL_ID> <FILE_ID> # Remove file from collection
│   │   └── delete <COLL_ID>      # Delete collection
│   └── query <QUERY>             # Direct vector search (no LLM)
│       ├── --collection <ID>     # Search in collection
│       ├── --file <ID>           # Search in file
│       ├── --top-k <N>           # Number of results (default: 5)
│       └── --threshold <FLOAT>   # Similarity threshold
│
├── functions                     # Custom Functions
│   ├── list                      # List installed functions
│   │   └── --enabled-only        # Show only enabled
│   ├── info <FUNC_ID>            # Function details
│   ├── install <URL|PATH>        # Install function
│   ├── enable <FUNC_ID>          # Enable function
│   ├── disable <FUNC_ID>         # Disable function
│   ├── update <FUNC_ID>          # Update function
│   └── delete <FUNC_ID>          # Delete function
│
├── pipelines                     # Pipeline Management
│   ├── list                      # List pipelines
│   ├── info <PIPE_ID>            # Pipeline details
│   ├── create <NAME>             # Create pipeline
│   │   └── --config <FILE>       # Pipeline config file
│   ├── update <PIPE_ID>          # Update pipeline
│   └── delete <PIPE_ID>          # Delete pipeline
│
├── admin                         # Admin Operations (requires admin role)
│   ├── users                     # User management
│   │   ├── list                  # List users
│   │   ├── create <EMAIL>        # Create user
│   │   ├── info <USER_ID>        # User details
│   │   ├── update <USER_ID>      # Update user
│   │   ├── delete <USER_ID>      # Delete user
│   │   └── set-role <USER_ID> <ROLE>
│   ├── config                    # Server configuration
│   │   ├── get [KEY]             # Get config value(s)
│   │   └── set <KEY> <VALUE>     # Set config value
│   └── stats                     # Usage statistics
│       ├── --period <PERIOD>     # day, week, month
│       └── --export              # Export as CSV
│
└── config                        # CLI Configuration
    ├── init                      # Initialize config file
    ├── show                      # Show current config
    ├── set <KEY> <VALUE>         # Set config value
    ├── get <KEY>                 # Get config value
    └── profiles                  # Profile management
        ├── list                  # List profiles
        ├── create <NAME>         # Create profile
        ├── use <NAME>            # Set default profile
        └── delete <NAME>         # Delete profile
```

---

## Technical Implementation

### Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Matches OpenWebUI backend |
| CLI Framework | `typer` | Modern, type-hints, auto-completion |
| HTTP Client | `httpx` | Async support, streaming |
| Output Formatting | `rich` | Beautiful terminal output |
| Config | `pydantic` + YAML | Type-safe configuration |
| Auth | `keyring` | Secure token storage |

### Project Structure

```
openwebui-cli/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── openwebui_cli/
│       ├── __init__.py
│       ├── __main__.py           # Entry point
│       ├── cli.py                # Main CLI app
│       ├── config.py             # Configuration management
│       ├── client.py             # HTTP client wrapper
│       ├── auth.py               # Authentication logic
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── auth.py           # auth subcommands
│       │   ├── chat.py           # chat subcommands
│       │   ├── models.py         # models subcommands
│       │   ├── rag.py            # rag subcommands
│       │   ├── functions.py      # functions subcommands
│       │   ├── pipelines.py      # pipelines subcommands
│       │   ├── admin.py          # admin subcommands
│       │   └── config_cmd.py     # config subcommands
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── text.py           # Plain text output
│       │   ├── json.py           # JSON output
│       │   └── table.py          # Table output
│       └── utils/
│           ├── __init__.py
│           ├── streaming.py      # SSE handling
│           └── progress.py       # Progress bars
└── tests/
    ├── __init__.py
    ├── test_auth.py
    ├── test_chat.py
    └── ...
```

### Configuration File

**Location:** `~/.config/openwebui/config.yaml` (Linux/macOS) or `%APPDATA%\\openwebui\\config.yaml` (Windows)

```yaml
# OpenWebUI CLI Configuration
version: 1

# Default profile
default_profile: local

# Profiles for different servers
profiles:
  local:
    uri: http://localhost:8080
    # Token stored in system keyring

  production:
    uri: https://openwebui.example.com
    # Token stored in system keyring

# CLI defaults
defaults:
  model: llama3.2:latest
  format: text
  stream: true

# Output preferences
output:
  colors: true
  progress_bars: true
  timestamps: false
```

### Token Handling & Precedence

**Token sources (in order of precedence):**

1. **CLI flag** (highest priority):
   ```bash
   openwebui --token "sk-xxxx..." chat send -m llama3.2 -p "Hello"
   ```

2. **Environment variable:**
   ```bash
   export OPENWEBUI_TOKEN="sk-xxxx..."
   openwebui chat send -m llama3.2 -p "Hello"
   ```

3. **System keyring** (lowest priority):
   - Automatically set after `openwebui auth login`
   - Stored under service name: `openwebui-cli`
   - Python implementation:
   ```python
   import keyring
   token = keyring.get_password("openwebui-cli", f"{profile}:{uri}")
   ```

**Headless/CI environments without keyring:**
```bash
# Option 1: Environment variable (recommended for CI)
export OPENWEBUI_TOKEN="sk-xxxx..."
openwebui chat send -m llama3.2 -p "Hello"

# Option 2: CLI flag (for scripts)
openwebui --token "sk-xxxx..." chat send -m llama3.2 -p "Hello"

# Option 3: Install lightweight backend
pip install keyrings.alt
```

**Token storage notes:** Tokens are stored securely in the system keyring by default (NOT in config file).
In headless/CI environments without a keyring backend, use `--token` or `OPENWEBUI_TOKEN` environment variable.
For a lightweight backend in CI/containers, install `keyrings.alt` in the runtime environment.

### Authentication Flow

```
1. First-time setup:
   $ openwebui auth login
   > Enter username: user@example.com
   > Enter password: ********
   > Token saved to keyring

2. Future (not implemented in v0.1.0-alpha):
   - OAuth flow (e.g., `openwebui auth login --oauth --provider google`)
   - API key management (`openwebui auth keys ...`)
   These are intentionally deferred to a later release; current auth is password + token storage (keyring/env/flag).
```

### Streaming Implementation

```python
async def stream_chat(client, model, prompt, **kwargs):
    """Stream chat completion with real-time output."""
    async with client.stream(
        "POST",
        "/api/v1/chat/completions",
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "stream": True},
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if content := data.get("choices", [{}])[0].get("delta", {}).get("content"):
                    print(content, end="", flush=True)
    print()  # Newline at end
```

---

## v1.0 MVP Scope (Ship This First)

These are the commands included in the **first PR / first release**:

### Top-level & Shared

**Global flags:**
- `--profile` - Use named profile from config
- `--uri` - Server URL
- `--format` - Output format (text, json, yaml)
- `--quiet` - Suppress non-essential output
- `--verbose/--debug` - Enable debug logging
- `--timeout` - Request timeout

**Config (v1.0):**
- `config init` - Initialize config file (interactive)
- `config show` - Show current config (redact secrets)
- `config set <KEY> <VALUE>` - Set config value (optional)

### Auth (v1.0)

- `auth login` - Interactive login (username/password)
- `auth logout` - Revoke current token
- `auth whoami` - Show current user info
- `auth token` - Show token info (type, expiry, not raw)
- `auth refresh` - Refresh token if available
- Token storage via `keyring` (no plaintext tokens in config)

*API keys (`auth keys`) deferred to v1.1 for smaller first cut.*

### Chat (v1.0)

- `chat send`
  - `--model | -m` - Model to use (required)
  - `--prompt | -p` - User prompt (or stdin)
  - `--chat-id` - Continue existing conversation
  - `--history-file` - Load history from file
  - `--no-stream` - Wait for complete response
  - `--format` + `--json` - Output format options
  - **Streaming ON by default** (from config)

*Chat history commands (`list/show/export/archive/delete`) deferred to v1.1.*

### RAG (v1.0 - Minimal)

- `rag files list` - List uploaded files
- `rag files upload <PATH>... [--collection <ID>]` - Upload file(s)
- `rag files delete <FILE_ID>` - Delete file
- `rag collections list` - List collections
- `rag collections create <NAME>` - Create collection
- `rag collections delete <COLL_ID>` - Delete collection
- `rag search <QUERY> --collection <ID> --top-k <N> --format json` - Vector search

### Models (v1.0)

- `models list` - List available models
- `models info <MODEL_ID>` - Show model details

*Model operations (`pull/delete/copy`) deferred to v1.1 depending on API maturity.*

### Admin (v1.0 - Minimal)

- `admin stats --format <text|json>` - Usage statistics
- RBAC enforced via server token
- Exit code `3` on permission errors

*Admin user/config management deferred to v1.1.*

---

## v1.1+ Enhancements (Next Iterations)

These are ideal follow-ups once v1.0 is stable:

### Auth & Keys (v1.1)

- `auth keys list` - List API keys
- `auth keys create [--name --scope ...]` - Create API key
- `auth keys revoke <KEY_ID>` - Revoke API key
- More structured scope model & docs (e.g. `read:chat`, `write:rag`, `admin:*`)

### Chat Quality-of-Life (v1.1)

- `chat list` - List conversations
- `chat show <CHAT_ID>` - Show conversation details
- `chat export <CHAT_ID> [--format markdown|json]` - Export conversation
- `chat archive/delete <CHAT_ID>` - Archive or delete
- `--system-prompt` or `--meta` support once server-side API supports rich metadata

### Models (v1.1)

- `models pull` - Pull/download model
- `models delete` - Delete model
- `models copy` - Copy/alias model
- Clear handling of local vs remote model registries

### RAG UX (v1.1+)

- `rag collections add <COLL_ID> <FILE_ID>...` - Add files to collection
- `rag collections ingest <COLL_ID> <PATH>...` - Upload + add in one go (v1.2+)

### Functions & Pipelines (v1.1+)

- `functions list/install/enable/disable/delete`
- `pipelines list/create/delete/run`
- Official JSON schema for pipeline configs & function manifests

### Developer Ergonomics (v1.1+)

- Shell completions: `openwebui --install-completion` / `--show-completion`
- Better error pretty-printing with `rich` (esp. for validation errors)

---

## Testing Strategy

### Unit Tests

Commands can be tested via pytest with mocked HTTP responses:

```python
# tests/test_chat.py
import pytest
from unittest.mock import patch, MagicMock
from openwebui_cli.commands.chat import send_chat

@pytest.mark.asyncio
async def test_chat_send_basic():
    """Test basic chat send functionality."""
    with patch('openwebui_cli.client.HTTPClient.post') as mock_post:
        mock_post.return_value = {"choices": [{"message": {"content": "Hello!"}}]}
        result = await send_chat(
            client=MagicMock(),
            model="llama3.2:latest",
            prompt="Hi"
        )
        assert result == "Hello!"
```

### Integration Tests

Test against a running OpenWebUI instance (docker-compose setup provided):

```bash
# Start local OpenWebUI for testing
docker-compose -f tests/docker-compose.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Clean up
docker-compose -f tests/docker-compose.yml down
```

### Testing Commands

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=openwebui_cli --cov-report=html

# Run specific test
pytest tests/test_auth.py::test_login

# Run tests marked as slow separately
pytest -m slow

# Run tests with verbose output and print statements
pytest -vv -s
```

---

## Implementation Checklist (22 Concrete Steps)

Use this as a PR checklist:

### A. Skeleton & CLI Wiring

- [x] **Create package layout** in monorepo:
   ```text
   openwebui-cli/
     pyproject.toml
     README.md
     docs/RFC.md
     openwebui_cli/
       __init__.py
       main.py
       config.py
       auth.py
       http.py
       errors.py
       commands/
         __init__.py
         auth.py
         chat.py
         config_cmd.py
         models.py
         admin.py
         rag.py
       formatters/
         __init__.py
       utils/
         __init__.py
   ```

- [x] **Wire Typer app** in `main.py`:
   - Main `app = typer.Typer()`
   - Sub-apps: `auth_app`, `chat_app`, `rag_app`, `models_app`, `admin_app`, `config_app`
   - Global options (profile, uri, format, quiet, verbose, timeout)

- [x] **Implement central HTTP client helper** in `http.py`:
   - Builds `httpx.AsyncClient` from resolved URI, timeout, auth headers
   - Token from keyring, env, or CLI flag
   - Standard error translation → `CLIError` subclasses

### B. Config & Profiles

- [x] **Implement config path resolution:**
   - Unix: XDG → `~/.config/openwebui/config.yaml`
   - Windows: `%APPDATA%\openwebui\config.yaml`

- [x] **Implement config commands:**
   - `config init` (interactive: ask URI, default model, default format)
   - `config show` (redact secrets, e.g. token placeholders)

- [x] **Implement config loading & precedence:**
   - Load file → apply profile → apply env → override with CLI flags

### C. Auth Flow

- [x] **Implement token storage using `keyring`:**
   - Key name: `openwebui:{profile}:{uri}`

- [x] **`auth login`:**
   - Prompt for username/password
   - Exchange for token using server's auth endpoint
   - Save token to keyring

- [x] **`auth logout`:**
   - Delete token from keyring

- [x] **`auth whoami`:**
   - Call `/api/v1/auths/` endpoint
   - Print name, email, roles

- [x] **`auth token`:**
   - Show minimal info: token type, expiry
   - Not the full raw token

- [ ] **`auth refresh`:** (v1.1+)
   - Call refresh endpoint if available
   - Update token in keyring
   - Exit code `3` if refresh fails due to auth

### D. Chat Send + Streaming

- [x] **Implement `chat send`:**
   - Resolve model, prompt, chat ID
   - Streaming support with `httpx` async streaming
   - Print tokens as they arrive with proper formatting
   - Handle Ctrl-C gracefully
   - Support `--no-stream` for full response

- [x] **Ensure exit codes follow the table:**
   - Usage errors → 2
   - Auth failures → 3
   - Network errors → 4
   - Server error (e.g., 500) → 5

### E. RAG Minimal API

- [x] **Implement `rag files list/upload/delete`:**
   - Upload: handle multiple paths; show IDs
   - `--collection` optional; attach uploaded files if provided

- [x] **Implement `rag collections list/create/delete`**

- [x] **Implement `rag search`:**
   - Vector search via API
   - Default `--format json`; text mode displays results
   - Return exit code `0` even for empty results; use `1` only on error

### F. Models & Admin

- [x] **Models:**
   - `models list` - List available models
   - `models info` - Show model details
   - Support `--format json|text|yaml`

- [x] **Admin:**
   - `admin stats` - Server statistics
   - Check permission errors → exit code `3` with clear message:
     > "Admin command requires admin privileges; your current user is 'X' with roles: [user]."

### G. Tests & Docs

- [x] **Add unit tests:**
   - Config precedence (test_config.py)
   - Exit code mapping (test_errors.py)
   - Auth flow (test_auth_cli.py)
   - Chat commands (test_chat.py)
   - RAG commands (test_rag.py)
   - Models & Admin (test_models.py, test_admin.py)

- [x] **Add comprehensive README:**
   - Installation & troubleshooting
   - Configuration with token precedence
   - Quick start examples
   - Complete usage guide
   - Development setup

- [x] **Update RFC documentation:**
   - Token handling & precedence
   - Testing strategy
   - Implementation checklist with status

---

## Usage Examples

### Basic Chat
```bash
# Simple chat
$ openwebui chat send -m llama3.2:latest -p "What is the capital of France?"
Paris is the capital of France.

# With system prompt
$ openwebui chat send -m llama3.2:latest \
    -s "You are a helpful coding assistant" \
    -p "Write a Python function to calculate fibonacci"

# From stdin (pipe)
$ echo "Explain quantum computing" | openwebui chat send -m llama3.2:latest

# Continue conversation
$ openwebui chat send -m llama3.2:latest --chat-id abc123 -p "Tell me more"
```

### RAG Workflow
```bash
# Upload documents
$ openwebui rag files upload ./docs/*.pdf
Uploaded: doc1.pdf (id: file-abc123)
Uploaded: doc2.pdf (id: file-def456)

# Create collection
$ openwebui rag collections create "Project Docs" --description "Project documentation"
Created collection: coll-xyz789

# Add files to collection
$ openwebui rag collections add coll-xyz789 file-abc123 file-def456
Added 2 files to collection

# Chat with RAG context
$ openwebui chat send -m llama3.2:latest \
    --collection coll-xyz789 \
    -p "Summarize the main points from these documents"
```

### Scripting & Automation
```bash
# Export chat history
$ openwebui chat export abc123 --format json > chat_backup.json

# Batch model pull
$ cat models.txt | xargs -I {} openwebui models pull {}

# List all collections as JSON (for scripting)
$ openwebui rag collections list --format json | jq '.[] | .id'

# Health check script
$ openwebui admin stats --format json | jq '.status'
```

---

## Contribution Strategy

### For OpenWebUI Core Team

1. **Proposal Review:** This document for initial feedback
2. **RFC Discussion:** Open GitHub Discussion for community input
3. **Implementation:** In `open-webui/cli` or separate repo initially
4. **Integration:** Merge into main repo as `openwebui-cli` package
5. **Release:** Alongside next minor version

### Packaging

```bash
# Install from PyPI (target)
pip install openwebui-cli

# Or with OpenWebUI
pip install open-webui[cli]

# Command available as
openwebui <command>
# or
open-webui-cli <command>
```

---

## Open Questions for Review

1. **Command naming:** `openwebui` vs `owui` vs `webui`?
2. **Scope:** Include admin commands in v1.0 or defer?
3. **Repository:** Separate repo or monorepo with open-webui?
4. **Streaming default:** On by default or opt-in?
5. **Config location:** `~/.openwebui/` vs `~/.config/openwebui/`?

---

## Appendix: API Endpoint Reference

Based on ChromaDB analysis of OpenWebUI source code:

### Authentication
```
POST /api/v1/auths/signin          - Sign in
POST /api/v1/auths/signup          - Sign up
POST /api/v1/auths/signout         - Sign out
GET  /api/v1/auths/                - Current user info
POST /api/v1/auths/api_key         - Create API key
DELETE /api/v1/auths/api_key       - Delete API key
```

### Chat
```
POST /api/v1/chat/completions      - Chat completion (OpenAI-compatible)
GET  /api/v1/chats/                - List chats
GET  /api/v1/chats/{id}            - Get chat
DELETE /api/v1/chats/{id}          - Delete chat
POST /api/v1/chats/{id}/archive    - Archive chat
```

### Models
```
GET  /api/models                   - List models
GET  /api/models/{id}              - Model info
POST /api/pull                     - Pull model (Ollama)
DELETE /api/models/{id}            - Delete model
```

### RAG
```
POST /api/v1/files/                - Upload file
GET  /api/v1/files/                - List files
DELETE /api/v1/files/{id}          - Delete file
GET  /api/v1/knowledge/            - List collections
POST /api/v1/knowledge/            - Create collection
DELETE /api/v1/knowledge/{id}      - Delete collection
```

### Functions & Pipelines
```
GET  /api/v1/functions/            - List functions
POST /api/v1/functions/            - Create function
GET  /api/v1/pipelines/            - List pipelines
POST /api/v1/pipelines/            - Create pipeline
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-30 | InfraFabric | Initial RFC |
| 1.2 | 2025-11-30 | InfraFabric + Grok Review | Added v1.0 MVP scope, v1.1+ roadmap, 22-step implementation checklist, exit code table |

---

*This proposal leverages 9,832 chunks of OpenWebUI source code, documentation, and issue analysis from our ChromaDB knowledge base to ensure comprehensive API coverage and alignment with user needs.*
