from __future__ import annotations

import pytest

import fashion_size.types as types


@pytest.fixture(autouse=True)
def _reset_host_hooks():
    """The display-language getter is a process global. Keep it from leaking between tests."""
    types._display_language = None
    yield
    types._display_language = None
