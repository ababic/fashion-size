"""Size types, locale conversion, and brand size charts.

Import ``Size``, ``Size.convert``, and ``Size.convert_to_locale`` from ``fashion_size.types``.
Django fields live in ``django-fashion-size``.
"""

from fashion_size.__version__ import __version__
from fashion_size.brands import SUPPORTED_BRANDS, BrandName
from fashion_size.demographics import Demographic
from fashion_size.product_types import (
    PRODUCT_TYPE_FAMILIES,
    PRODUCT_TYPES,
    ProductType,
    ProductTypeFamily,
)
from fashion_size.types import (
    ConversionSource,
    ConversionSourceKind,
    DefaultChartReason,
    register_display_language,
)

__all__ = [
    "BrandName",
    "ConversionSource",
    "ConversionSourceKind",
    "DefaultChartReason",
    "Demographic",
    "PRODUCT_TYPE_FAMILIES",
    "PRODUCT_TYPES",
    "ProductType",
    "ProductTypeFamily",
    "SUPPORTED_BRANDS",
    "__version__",
    "register_display_language",
]
