# Contributing to OpenWebUI CLI

Thanks for helping improve the CLI! This guide keeps contributions consistent and easy to review.

## Getting started

1) Clone and create a virtualenv (Python 3.11+):

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

2) Run the quality gates locally:

```bash
ruff check openwebui_cli
mypy openwebui_cli --ignore-missing-imports
pytest tests/ --cov=openwebui_cli
```

3) Keep changes small and focused. Include tests for new behavior or bug fixes.

## Pull request checklist

- [ ] Tests pass (including new coverage for your change).
- [ ] No new lint/type errors.
- [ ] Docs updated (README or docs/guides) if behavior changes.
- [ ] Avoid breaking CLI surface or config formats without discussion.

## Coding style

- Typer for CLI, httpx for HTTP, rich for output.
- Prefer clear error messages; use the shared error helpers in `openwebui_cli.errors`/`http`.
- Keep tokens out of logs; prefer keyring/env/flag handling already in place.

## Filing issues

When reporting a bug, include:
- CLI command and flags used
- Expected vs actual behavior
- Relevant logs/tracebacks (sanitized)
- OpenWebUI server version and CLI version

## Security reports

Please do **not** open public issues for security problems. See `SECURITY.md` for the private contact path.
