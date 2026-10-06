"""Brand conversion charts.

Each override chart is a JSON file named by UUID. The file holds the conversion
rows, the source page, and notes about that table. Which brand it belongs to,
and when it was last checked, are recorded on ``fashion_size.brands.BRANDS``.
A brand with no charts matches the defaults.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from fashion_size.brands import BRANDS, BrandName, OverrideChart, resolve_brand_name
from fashion_size.demographics import AgeGroup, Gender
from fashion_size.product_types import (
    PRODUCT_TYPE_SLUGS,
    ProductType,
    resolve_product_type,
)
from fashion_size.size_types import SizeTypeSlug


@dataclass(frozen=True, slots=True)
class BrandConversionChart:
    """One brand chart for a size type, age group, gender, and set of product types."""

    brand_name: BrandName
    size_type: str
    age_group: str
    gender: str
    product_types: tuple[ProductType, ...]
    updated_at: datetime
    source_url: str
    source_notes: str
    rows: tuple[dict[str, float | int | str], ...]

    def covers(self, product_type: ProductType | str) -> bool:
        """Whether this chart replaces the default for ``product_type``.

        A chart with no product types covers every product type.
        """
        if not self.product_types:
            return True
        try:
            return resolve_product_type(product_type) in self.product_types
        except ValueError:
            return False


def _chart_directory() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "charts"


def _validate_override(brand_name: str, chart: OverrideChart) -> None:
    try:
        parsed_id = uuid.UUID(chart.id)
    except ValueError as exc:
        raise ValueError(
            f"Chart id {chart.id!r} on {brand_name!r} is not a UUID."
        ) from exc
    if str(parsed_id) != chart.id:
        raise ValueError(
            f"Chart id {chart.id!r} on {brand_name!r} must be a lowercase UUID."
        )
    if chart.size_type not in SizeTypeSlug:
        raise ValueError(f"Unknown size type {chart.size_type!r} on {brand_name!r}.")
    if chart.age_group not in AgeGroup:
        raise ValueError(f"Unknown age group {chart.age_group!r} on {brand_name!r}.")
    if chart.gender not in {"", Gender.MALE, Gender.FEMALE}:
        raise ValueError(f"Unknown chart gender {chart.gender!r} on {brand_name!r}.")
    unknown = [
        product_type
        for product_type in chart.product_types
        if product_type not in PRODUCT_TYPE_SLUGS
    ]
    if unknown:
        raise ValueError(f"Unknown product types {unknown!r} on {brand_name!r}.")
    if chart.updated_at.tzinfo is None:
        raise ValueError(
            f"Review date for {brand_name!r} chart {chart.id} must include a timezone."
        )


@dataclass(frozen=True, slots=True)
class _StoredChart:
    """Rows and provenance read from one chart file."""

    source_url: str
    source_notes: str
    rows: tuple[dict[str, float | int | str], ...]


def _parse_rows(
    chart_id: str, rows: object
) -> tuple[dict[str, float | int | str], ...]:
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{chart_id} chart has no rows.")
    normalised_rows: list[dict[str, float | int | str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"uk", "eu", "us", "au"}:
            raise ValueError(f"{chart_id} chart row must have uk, eu, us, and au.")
        normalised: dict[str, float | int | str] = {}
        for key in ("uk", "eu", "us", "au"):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, str | int | float):
                raise ValueError(
                    f"{chart_id} chart has an invalid {key} value {value!r}."
                )
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{chart_id} chart has an empty {key} value.")
            normalised[key] = value
        normalised_rows.append(normalised)
    return tuple(normalised_rows)


def _read_chart_file(path: Path) -> _StoredChart:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    chart_id = path.stem
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported chart schema in {path.name}.")
    expected = {"schema_version", "source_url", "source_notes", "rows"}
    if set(payload) != expected:
        raise ValueError(
            f"{path.name} must contain schema_version, source_url, source_notes, and rows."
        )
    source_url = payload["source_url"]
    source_notes = payload["source_notes"]
    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError(f"{chart_id} chart source_url must be a non-empty string.")
    if not isinstance(source_notes, str):
        raise ValueError(f"{chart_id} chart source_notes must be a string.")
    return _StoredChart(
        source_url=source_url,
        source_notes=source_notes,
        rows=_parse_rows(chart_id, payload["rows"]),
    )


@cache
def _load_brands() -> tuple[tuple[str, tuple[BrandConversionChart, ...]], ...]:
    """``(brand name, charts)`` for every brand in the catalog.

    Names stay in catalog order. A brand whose published guide matches the defaults
    has an empty chart tuple. Each override's rows and source are loaded from its
    UUID file.
    """
    files = {path.stem: path for path in _chart_directory().glob("*.json")}
    names = [brand.name.casefold() for brand in BRANDS]
    if len(names) != len(set(names)):
        raise ValueError("Two brands share a name.")
    seen_ids: set[str] = set()
    loaded: list[tuple[str, tuple[BrandConversionChart, ...]]] = []
    for brand in BRANDS:
        parsed: list[BrandConversionChart] = []
        for override in brand.charts:
            _validate_override(brand.name, override)
            if override.id in seen_ids:
                raise ValueError(f"Chart {override.id} is listed more than once.")
            seen_ids.add(override.id)
            path = files.get(override.id)
            if path is None:
                raise ValueError(f"No chart file for {override.id} ({brand.name}).")
            stored = _read_chart_file(path)
            parsed.append(
                BrandConversionChart(
                    brand_name=brand.name,
                    size_type=override.size_type,
                    age_group=override.age_group,
                    gender=override.gender,
                    product_types=override.product_types,
                    updated_at=override.updated_at,
                    source_url=stored.source_url,
                    source_notes=stored.source_notes,
                    rows=stored.rows,
                )
            )
        loaded.append((brand.name, tuple(parsed)))
    orphans = sorted(set(files) - seen_ids)
    if orphans:
        raise ValueError(
            f"Chart files are not listed on a brand: {', '.join(orphans)}."
        )
    if not seen_ids:
        raise ValueError("No override charts are shipped.")
    return tuple(loaded)


def load_brand_charts() -> tuple[BrandConversionChart, ...]:
    """Every shipped override chart.

    Brands stay in catalog order, and each brand's charts stay in catalog order.
    Brands that match the default charts are omitted.
    """
    return tuple(chart for _, charts in _load_brands() for chart in charts)


def charts_for_brand(brand_name: BrandName | str) -> tuple[BrandConversionChart, ...]:
    """Charts for a catalog brand. An unknown name has none."""
    known = resolve_brand_name(brand_name)
    if known is None:
        return ()
    return tuple(chart for chart in load_brand_charts() if chart.brand_name == known)


def chart_for(
    brand_name: BrandName | str,
    size_type: str,
    age_group: str,
    gender: str,
    product_type: ProductType | str | None = None,
) -> BrandConversionChart | None:
    """Pick a brand chart for this size type, demographic, and optional product type.

    A chart that lists ``product_type`` wins over a chart with no product types
    (one chart for every product type). When ``product_type`` is omitted, a chart
    for that size type and demographic is returned only when there is exactly one.
    A male or female chart wins over a chart with a blank gender (the shared chart
    for that age group).
    """
    age = age_group.strip().lower()
    sex = gender.strip().lower()
    size_type_slug = size_type.strip().lower()
    if product_type is not None and str(product_type).strip():
        product_type = resolve_product_type(product_type)
    else:
        product_type = None
    candidates = [
        chart
        for chart in charts_for_brand(brand_name)
        if chart.size_type == size_type_slug
        and chart.age_group == age
        and chart.gender in {sex, ""}
    ]
    if product_type:
        explicit = [
            chart for chart in candidates if product_type in chart.product_types
        ]
        pool = explicit or [chart for chart in candidates if not chart.product_types]
        gendered = [chart for chart in pool if chart.gender == sex]
        candidates = gendered or pool
    elif sex:
        gendered = [chart for chart in candidates if chart.gender == sex]
        if gendered:
            candidates = gendered
    if len(candidates) == 1:
        return candidates[0]
    return None
