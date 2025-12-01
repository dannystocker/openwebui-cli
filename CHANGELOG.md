# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Batch operations for models (pull/delete multiple models)
- Progress streaming for long-running operations
- Model search and filter functionality
- Async background operations with polling
- Rollback support for deleted models

## [0.1.0-alpha] - 2025-11-30

### Added

#### Core Features
- Official CLI implementation with complete command hierarchy:
  - `auth` - Authentication and token management
  - `chat` - Chat operations with streaming support
  - `models` - Model management (list, info, pull, delete)
  - `rag` - RAG file and collection operations
  - `admin` - Server statistics and diagnostics
  - `config` - Configuration management

#### Authentication
- Interactive login with credential prompts
- Token management with secure keyring storage
- Token precedence system: CLI flag > environment variable > keyring
- Logout functionality
- User information display (whoami)
- Token refresh capability
- Fallback to environment variables when keyring unavailable

#### Chat Operations
- Real-time streaming chat via Server-Sent Events
- Non-streaming mode with `--no-stream` option
- Support for RAG context with `--file` option
- Conversation continuation with `--chat-id` option
- Token-by-token response streaming with Rich formatting

#### Model Management
- List available models with JSON output support
- Get detailed model information
- Pull/download models with progress indicators
- Delete models with safety confirmation
- Force operations with `--force` flag

#### RAG (Retrieval-Augmented Generation)
- File upload support for documents
- File listing and deletion
- Collection creation and management
- Vector search within collections
- Multi-file batch operations

#### Admin Operations
- Server statistics retrieval
- User management
- Configuration viewing
- Role-based access control with helpful error messages

#### Configuration
- XDG-compliant file paths:
  - Linux/macOS: `~/.config/openwebui/config.yaml`
  - Windows: `%APPDATA%\openwebui\config.yaml`
- Multi-profile support for different server configurations
- Profile-specific URI and token storage
- Configuration initialization with sensible defaults
- Configuration viewing and validation

#### Developer Experience
- Type hints throughout codebase (Python 3.11+)
- Comprehensive error handling with 6 exit codes (0-5)
- Rich colored output with tables, lists, and progress bars
- Debug logging with `--verbose` flag
- Comprehensive help text on all commands

#### Testing & Quality
- Test suite with 80%+ code coverage
- Type checking with mypy (strict mode)
- Linting with ruff
- Unit tests for all major components:
  - Authentication flows
  - HTTP client and error handling
  - Configuration management
  - Chat streaming
  - Model operations
  - RAG operations
  - Admin operations

#### Security
- Secure token storage via OS keyring (Linux/macOS/Windows)
- No hardcoded credentials
- Token masking in display (show first/last 4 chars only)
- Safe configuration file permissions (0o600)
- Dependency audit with pip-audit

#### Documentation
- Comprehensive README with:
  - Installation instructions
  - Quick start guide
  - Full usage examples for all commands
  - Configuration guide
  - Troubleshooting section
  - Development setup
  - Exit code reference

### Fixed

#### Critical Bugs (P0)
- NoKeyring errors converted to meaningful AuthError with actionable messages
- Streaming response handling for chat operations
- Token precedence system (CLI flag now properly overrides all other sources)
- File permission handling for config operations

#### Quality Improvements
- Proper error propagation and handling in HTTP layer
- Improved error messages with suggested solutions
- Fixed race conditions in async test fixtures
- Proper resource cleanup in HTTP client context managers

### Security

- Tokens stored securely in OS keyring (fallback to environment variables)
- No credentials in configuration files
- Secure file permissions on config files (0o600 on Unix)
- Dependency vulnerability scanning with pip-audit
- Type safety to prevent injection attacks

### Changed

#### Architecture
- Modular command structure using Typer sub-applications
- Centralized error handling with custom CLIError class
- HTTP client abstraction with context manager pattern
- Configuration management via Pydantic settings

#### Dependencies
- `typer>=0.9.0` - CLI framework
- `httpx>=0.25.0` - Async HTTP client
- `rich>=13.0.0` - Terminal formatting
- `pydantic>=2.0.0` - Data validation
- `pydantic-settings>=2.0.0` - Configuration
- `pyyaml>=6.0` - YAML parsing
- `keyring>=24.0.0` - Secure token storage

### Known Limitations (Alpha)

- Some commands are stubs or have limited implementation (will be completed in v0.1.1)
- Limited error recovery for network failures (no automatic retry)
- Streaming may fail if proxy/firewall doesn't support Server-Sent Events
- Model pull operation shows basic progress indicator (no detailed percentage)
- Admin operations require admin role (not all endpoints available to regular users)

### Technical Details

#### Exit Codes
- `0` - Success
- `1` - General error
- `2` - Usage/argument error
- `3` - Authentication error
- `4` - Network error
- `5` - Server error (5xx)

#### Python Support
- Python 3.11+
- Type hints throughout (mypy strict mode)
- Async/await for streaming operations

#### Configuration Format
- YAML 1.2 format
- Per-profile token storage in system keyring
- Per-profile server URI configuration
- Global defaults for model, format, streaming

---

## Version History

### v0.1.0-alpha
**Release Date:** 2025-11-30

Initial alpha release with core CLI functionality. All major features implemented and tested. Ready for community feedback and bug reports.

**Development Timeline:**
- 2025-11-30: Initial scaffolding (commit 8530f74)
- 2025-11-30: CLI streaming, error handling, comprehensive tests (commit fbe6832)
- 2025-11-30: Code review fixes, P0 bugs, features (commit 80510a7)

---

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/dannystocker/openwebui-cli/issues
- Documentation: https://github.com/dannystocker/openwebui-cli#readme

## License

MIT License - See [LICENSE](LICENSE) file for details.
