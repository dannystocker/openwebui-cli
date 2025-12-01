"""Tests for main CLI --version flag."""

import re
import pytest
from typer.testing import CliRunner

from openwebui_cli.main import app
from openwebui_cli import __version__

runner = CliRunner()


def test_version_flag_prints_version():
    """Test --version prints version and exits cleanly."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "version" in result.output.lower()
    # Check version pattern (e.g., "0.1.0")
    assert re.search(r"\d+\.\d+\.\d+", result.output) is not None


def test_version_flag_short_form():
    """Test -v short form of --version."""
    result = runner.invoke(app, ["-v"])

    assert result.exit_code == 0
    assert "version" in result.output.lower()
    # Check version pattern
    assert re.search(r"\d+\.\d+\.\d+", result.output) is not None


def test_version_shows_correct_version():
    """Test --version shows the actual version from __version__."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    # Check that the actual version string is present
    assert __version__ in result.output


def test_version_output_not_empty():
    """Test --version outputs something."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert len(result.output.strip()) > 0


def test_version_flag_with_other_flags():
    """Test --version works alongside other flags."""
    # Version should take precedence and exit immediately
    result = runner.invoke(app, ["--version", "--verbose"])

    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_version_matches_module_version():
    """Test that printed version matches module __version__."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    # The output should contain the actual version string from __init__.py
    assert __version__ in result.output
    # Also verify version is in proper format
    assert result.output.count(".") >= 2  # At least X.Y.Z format
