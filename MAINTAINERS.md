# Maintainers

| Name            | Role              | Contact                    |
| --------------- | ----------------- | -------------------------- |
| OpenWebUI Team  | Core maintainers  | security@openwebui.com     |
| Community PRs   | Triage/Review     | via GitHub issues/PRs      |

## Supported targets
- Python: 3.11, 3.12
- OpenWebUI server: current stable release (see OpenWebUI docs)

## Release process
- Run CI (ruff, mypy, pytest, pip-audit) on main.
- Update `CHANGELOG.md` and `RELEASE_NOTES.md`.
- Tag versions matching `pyproject.toml` (`vX.Y.Z`), publish to PyPI.
