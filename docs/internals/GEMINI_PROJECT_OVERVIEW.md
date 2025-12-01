# OpenWebUI CLI – Project Guide (for Gemini)

This is a self-contained brief of the OpenWebUI CLI project for fast onboarding.

## What it is
- Official CLI wrapper for an OpenWebUI server (chat, auth, RAG, models, admin, config).
- Typer + httpx + rich; tokens stored in keyring (service `openwebui-cli`) with env/flag overrides.
- Tested, typed, linted; ~90% coverage.

## Layout (key files)
- `openwebui_cli/main.py` – Typer root (`openwebui`) with global options (`--profile`, `--uri`, `--token`, `--format`, `--timeout`, `--verbose`, `--quiet`, `--version`).
- `openwebui_cli/commands/`
  - `auth.py` – login/logout/whoami/token/refresh; login can prompt or read stdin; stores token in keyring; accepts `--token`/`OPENWEBUI_TOKEN`.
  - `chat.py` – `chat send` with streaming SSE or non-stream; system prompts, history files, RAG context (`--file/--collection`), `--chat-id`, temperature/max-tokens, JSON output.
  - `rag.py` – files list/upload/delete; collections list/create/delete; `rag search` vector query.
  - `models.py` – list/info; pull/delete placeholders.
  - `admin.py` – stats (with fallback role check), users/config placeholders but tested responses.
  - `config_cmd.py` – config init/show/set/get helpers.
- `openwebui_cli/http.py` – httpx client builders (sync/async), token resolution (CLI/env/keyring), keyring fallback, auth/network/server error helpers.
- `openwebui_cli/config.py` – pydantic config + env Settings; config path `~/.config/openwebui/config.yaml` (or `%APPDATA%\openwebui\config.yaml`).
- `openwebui_cli/errors.py` – Exit codes (0–5) and CLIError subclasses.
- Tests: `tests/` (admin/auth/auth_cli/chat/config/errors/http/models/rag). Coverage ~90% (`pytest --cov=openwebui_cli`).
- Docs/prompts: `README.md`, `docs/RFC.md`, `CHANGELOG.md`, `RELEASE_NOTES.md`, `QUICK_EVAL_PROMPT.md`, `CODEX_EVALUATION_PROMPT.md`, `SWARM_COMPLETION_REPORT.md`, `IMPLEMENTATION_REPORT.md`.

## How tokens work
- Resolution order: CLI `--token` or env `OPENWEBUI_TOKEN` → keyring (`openwebui-cli`, key `<profile>:<uri>`). If no keyring backend, AuthError suggests installing `keyrings.alt` or using `--token`.
- Login stores token in keyring; logout deletes it; token command can show/mask token; whoami uses current token.

## Chat behavior
- Builds messages from history file (list or `{messages: [...]}`) + optional system prompt + current user prompt.
- Streaming mode: SSE `data: ...` chunks accumulate and print incrementally; Ctrl-C yields graceful exit; JSON mode prints `{content: ...}`.
- Non-stream mode: POST `/api/v1/chat/completions`, prints content or JSON.
- Adds RAG context (`files` list) and `chat_id`, temperature, max_tokens when provided.

## RAG, models, admin
- RAG: `/api/v1/files/` (list/upload/delete), `/api/v1/knowledge/` (collections), `/api/v1/knowledge/{collection}/query` (search).
- Models: `/api/models` list, `/api/models/{id}` info; pull/delete currently placeholders with user-facing warnings.
- Admin: `/api/v1/admin/stats` (fallback to `/api/v1/auths/` role check); users/config commands are stubbed but tested for messaging and formatting.

## Configuration
- `Config` (defaults: profile `default`, uri `http://localhost:8080`, stream=True, timeout=30, format=text).
- `Settings` env overrides: `OPENWEBUI_URI`, `OPENWEBUI_TOKEN`, `OPENWEBUI_PROFILE`.
- Helpers: `get_effective_config` resolves profile/uri precedence (CLI > env > file > defaults); `save_config` writes YAML.

## QA commands
- Install dev: `pip install -e ".[dev]"` (use `.venv` already in repo).
- Tests: `.venv/bin/pytest tests/ --cov=openwebui_cli`
- Lint: `.venv/bin/ruff check openwebui_cli`
- Types: `.venv/bin/mypy openwebui_cli --ignore-missing-imports`
- Audit: `.venv/bin/pip-audit`
- Entry point: `.venv/bin/openwebui --help`

## Recent status (from last run)
- Pytest: 256 passed / 1 skipped, coverage ~90% (main gap: chat streaming edges covered by tests).
- Ruff/mypy/pip-audit: clean.
- Pip version: 25.3 inside `.venv`.

## Notable behaviors & edge cases
- CLIError handled in `main.cli()` to exit with defined codes.
- Keyring errors mapped to AuthError with guidance.
- History file validation (existence, JSON decode, shape).
- Streaming Ctrl-C returns exit code 0 after printing partial output notice.
- Placeholders (models pull/delete, admin users/config) emit yellow warnings—tested expectations.

## Useful paths for Gemini
- Root: `/home/setup/openwebui-cli`
- Venv: `.venv`
- Config file: `~/.config/openwebui/config.yaml` (uses temp dirs in tests)
- Keyring service: `openwebui-cli`

## Quick checklist to validate locally
1) `.venv/bin/openwebui --help` (commands present).
2) `.venv/bin/pytest tests/ --cov=openwebui_cli`
3) `.venv/bin/mypy openwebui_cli --ignore-missing-imports`
4) `.venv/bin/ruff check openwebui_cli`
5) `.venv/bin/pip-audit`

## If you need feature context
- See `docs/RFC.md` for CLI spec expectations and token/keyring notes.
- See `CHANGELOG.md` and `RELEASE_NOTES.md` for recent worklog.
- See `SWARM_COMPLETION_REPORT.md` / `IMPLEMENTATION_REPORT.md` for swarm agent outputs (informational).

With this file you should be able to navigate the code, run tests, and extend functionality without additional context.
