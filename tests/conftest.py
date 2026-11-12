"""Pytest configuration and Windows-safe fixtures."""

from pathlib import Path
import tempfile
import pytest


@pytest.fixture
def tmp_path():
    """Windows-safe temporary directory fixture with ignore_cleanup_errors."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
        yield Path(temp_dir)
