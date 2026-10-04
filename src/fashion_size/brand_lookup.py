"""Host hook for converting with a brand's own chart.

This package does not know about a brand model. The host app registers a
callable (the warehouse uses ``measurements.models.convert_for_brand``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

BrandConverter = Callable[..., Any]

_brand_converter: BrandConverter | None = None


def register_brand_converter(converter: BrandConverter) -> None:
    """Use ``converter`` when a ``MeasurementValue`` converts for a brand."""
    global _brand_converter
    _brand_converter = converter


def convert_with_brand(*args: Any, **kwargs: Any) -> Any:
    """Call the registered brand converter."""
    if _brand_converter is None:
        raise RuntimeError(
            "No brand converter is registered. Call fashion_size.register_brand_converter() from the host application."
        )
    return _brand_converter(*args, **kwargs)
