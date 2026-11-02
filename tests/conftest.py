"""
Shared pytest configuration and fixtures.

This conftest is discovered by pytest automatically at the top of the
tests/ directory and applies to all test modules.
"""

from __future__ import annotations

import pytest

from regularag.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings LRU cache before each test.

    This ensures that monkeypatched environment variables take effect
    by forcing the settings object to be reconstructed.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
