"""Size types, locale conversion, and brand size charts.

Import ``Size``, ``Size.convert_to_locale``, and ``Size.convert_to_unit`` from ``fashion_size.types``.
Django fields live in ``django-fashion-size``.
"""

from fashion_size.__version__ import __version__
from fashion_size.brands import SUPPORTED_BRANDS, BrandName
from fashion_size.product_types import PRODUCT_TYPES, ProductType
from fashion_size.types import register_display_language

__all__ = [
    "BrandName",
    "PRODUCT_TYPES",
    "ProductType",
    "SUPPORTED_BRANDS",
    "__version__",
    "register_display_language",
]
