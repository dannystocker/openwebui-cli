# Configuration Guide

The CLI reads settings from CLI flags, environment variables, and a config file.

## Precedence

`CLI flags` → `environment variables` → `config file` → defaults.

## Config file locations

- Linux/macOS: `~/.config/openwebui/config.yaml`
- Windows: `%APPDATA%\openwebui\config.yaml`

## Example config

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

## Environment variables

- `OPENWEBUI_PROFILE` – override profile name
- `OPENWEBUI_URI` – override server URI
- `OPENWEBUI_TOKEN` – token when keyring is unavailable or in CI

## Tokens and keyring

- Tokens are stored in system keyring under service `openwebui-cli` (key `<profile>:<uri>`).
- If no keyring backend is available, pass `--token` or set `OPENWEBUI_TOKEN`.
- For headless/CI, install a lightweight backend (e.g., `keyrings.alt`) or rely on env/flags.

## Profiles

- Set default profile via `openwebui config init` or editing the config file.
- Override per command with `--profile NAME` (and optionally `--uri`).

## Output formats

- Global `--format` flag accepts `text`, `json`, `yaml`.
- Defaults are stored under `defaults.format` in the config.
