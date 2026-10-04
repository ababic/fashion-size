"""Kind-specific fashion measurements and brand size-chart conversion.

Import measurements and ``MeasurementValue.convert`` from ``fashion_size.types``.
Django fields live in ``django-fashion-size``.
"""

from fashion_size.__version__ import __version__
from fashion_size.brand_lookup import register_brand_converter
from fashion_size.brands import SUPPORTED_BRANDS
from fashion_size.guides import OVERRIDE_GUIDES, OverrideGuide
from fashion_size.types import register_display_language

__all__ = [
    "OVERRIDE_GUIDES",
    "OverrideGuide",
    "SUPPORTED_BRANDS",
    "__version__",
    "register_brand_converter",
    "register_display_language",
]
