"""Brands whose size guides this package can convert.

Each brand has a JSON file in ``fashion_size/fixtures/brands``. A file with
charts replaces the default for those rows. A file with no charts means the
published guide matches the defaults. Brands with no garment size system
(homeware, made-to-measure, promotional merch) are omitted.
"""

from __future__ import annotations

from fashion_size.charts import supported_brand_names

SUPPORTED_BRANDS: tuple[str, ...] = supported_brand_names()
