from __future__ import annotations

import pytest

import fashion_size.brand_lookup as brand_lookup
import fashion_size.types as types


@pytest.fixture(autouse=True)
def _reset_host_hooks():
    """Host hooks are process globals. Keep them from leaking between tests."""
    types._display_language = None
    brand_lookup._brand_converter = None
    yield
    types._display_language = None
    brand_lookup._brand_converter = None
