# OpenWebUI CLI

[![CI](https://github.com/open-webui/openwebui-cli/workflows/CI/badge.svg)](https://github.com/open-webui/openwebui-cli/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()

Official command-line interface for [OpenWebUI](https://github.com/open-webui/open-webui).

> Status: Alpha (v0.1.0) — tested, linted, ~90% coverage. Known limitations: OAuth/provider login and API key management are not implemented yet; models pull/delete depend on server support.

## Features
- Authentication & token management (keyring + env + `--token`)
- Profiles for multiple OpenWebUI instances
- Chat with streaming/non-streaming modes, history, RAG context
- RAG files/collections (list, upload, delete, search)
- Model info/list (pull/delete supported when server supports it)
- Admin stats/users/config (admin role required)
- JSON/YAML/text output with Rich formatting

## Installation

```bash
pip install openwebui-cli
# or from source
git clone https://github.com/dannystocker/openwebui-cli.git
cd openwebui-cli
pip install -e .
```

### Requirements
- Python 3.11+
- OpenWebUI server reachable at your chosen `--uri`

## Quick start
```bash
# 1) Init config (creates ~/.config/openwebui/config.yaml)
openwebui config init

# 2) Login (stores token in keyring, or use --token/OPENWEBUI_TOKEN)
openwebui auth login

# 3) Chat (streaming by default)
openwebui chat send -m llama3.2:latest -p "Hello from the CLI"

# 4) RAG search
openwebui rag search --query "deployment steps" --collection my-coll
```

## Commands overview

| Area   | Examples                                                  | Notes                                   |
| ------ | --------------------------------------------------------- | --------------------------------------- |
| Auth   | `openwebui auth login`, `logout`, `whoami`, `token`, `refresh` | Tokens via keyring/env/`--token`        |
| Chat   | `openwebui chat send --prompt "Hello"`                    | Streaming/non-streaming, RAG context    |
| Models | `openwebui models list`, `info MODEL_ID`                  | Pull/delete currently placeholders      |
| RAG    | `openwebui rag files list`, `collections list`, `search`  | Upload/search files & collections       |
| Config | `openwebui config init`, `show`, `set`, `get`             | Profiles, defaults, output options      |
| Admin  | `openwebui admin stats`, `users`, `config`                | Admin-only endpoints (role required)    |

See `docs/commands/README.md` for a compact reference.

### Global options (all commands)

| Option | Description |
| ------ | ----------- |
| `-v, --version` | Show version and exit |
| `-P, --profile` | Profile name to use |
| `-U, --uri` | Override server URI |
| `--token` | Bearer token (overrides env/keyring) |
| `-f, --format` | Output format: `text`, `json`, `yaml` |
| `-q, --quiet` | Suppress non-essential output |
| `--verbose` | Enable debug logging |
| `-t, --timeout` | Request timeout in seconds |

## Configuration

Config precedence: `CLI flags` → `environment variables` → `config file` → defaults.

- Config file: `~/.config/openwebui/config.yaml` (Linux/macOS) or `%APPDATA%\openwebui\config.yaml` (Windows).
- Env vars: `OPENWEBUI_PROFILE`, `OPENWEBUI_URI`, `OPENWEBUI_TOKEN`.
- Tokens: stored in keyring (`openwebui-cli` service, key `<profile>:<uri>`). If no keyring backend, use `--token` or `OPENWEBUI_TOKEN`; in headless/CI, install `keyrings.alt` or rely on env.
- Example config:

```yaml
version: 1
default_profile: default
profiles:
  default:
    uri: http://localhost:8080
defaults:
  model: llama3.2:latest
  format: text
  stream: true
  timeout: 30
output:
  colors: true
  progress_bars: true
  timestamps: false
```

More details: `docs/guides/configuration.md`.

## Usage examples

- Non-streaming chat with JSON output:
  ```bash
  openwebui chat send -m my-model -p "Summarize" --no-stream --json
  ```
- Continue a conversation:
  ```bash
  openwebui chat send --chat-id CHAT123 -p "Tell me more"
  ```
- Shell completions:
  ```bash
  openwebui --install-completion bash
  openwebui --install-completion zsh
  openwebui --install-completion fish
  ```
- RAG file upload + search:
  ```bash
  openwebui rag files upload ./docs/*.pdf
  openwebui rag search --query "auth flow" --collection my-coll
  ```
- Use a different profile and token:
  ```bash
  openwebui --profile prod --token "$PROD_TOKEN" chat send -p "Ping prod"
  ```

## Troubleshooting

- **No keyring backend available:** pass `--token` or set `OPENWEBUI_TOKEN`; or install `keyrings.alt`.
- **401/Forbidden:** re-login `openwebui auth login` or refresh token; verify `--uri` and profile.
- **Connection issues:** check server is reachable; override with `--uri`; increase `--timeout`.
- **Invalid history file:** ensure JSON array or `{ "messages": [...] }`.

## Exit codes

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
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
ruff check openwebui_cli
mypy openwebui_cli --ignore-missing-imports
pytest tests/ --cov=openwebui_cli
```

## Contributing and community
- Contribution guide: `CONTRIBUTING.md`
- Code of Conduct: `CODE_OF_CONDUCT.md`
- Security policy: `SECURITY.md`
- RFC: `docs/RFC.md`

## License

MIT License - see [LICENSE](LICENSE).

## Credits

Created and maintained by **Danny Stocker** at [if.](https://digital-lab.ca/dannystocker/)
