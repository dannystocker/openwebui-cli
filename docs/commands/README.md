# Command Overview

Quick reference for the OpenWebUI CLI commands. Use `--help` on any command for full options.

| Area   | Examples                                                  | Notes                                   |
| ------ | --------------------------------------------------------- | --------------------------------------- |
| Auth   | `openwebui auth login`, `logout`, `whoami`, `token`, `refresh` | Tokens via keyring/env/`--token`        |
| Chat   | `openwebui chat send --prompt "Hello"`                    | Streaming/non-streaming, RAG context    |
| Models | `openwebui models list`, `info MODEL_ID`                  | Pull/delete currently placeholders      |
| RAG    | `openwebui rag files list`, `collections list`, `search`  | Upload/search files & collections       |
| Config | `openwebui config init`, `show`, `set`, `get`             | Profiles, defaults, output options      |
| Admin  | `openwebui admin stats`, `users`, `config`                | Admin-only endpoints (role required)    |

Global options (all commands):

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

For configuration details, see `../guides/configuration.md`.
