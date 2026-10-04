"""Brand conversion charts.

Each override chart is a JSON file of rows, named by UUID. Which brand it
belongs to, when it was last checked, and the source page are recorded on
``fashion_size.brands.BRANDS``. A brand with no charts matches the defaults.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from fashion_size.brands import BRANDS, OverrideChart
from fashion_size.demographics import AgeGroup, Gender
from fashion_size.guides import OVERRIDE_GUIDE_SLUGS
from fashion_size.kinds import KindSlug


@dataclass(frozen=True, slots=True)
class BrandConversionChart:
    """One brand chart for a kind, age group, gender, and set of guides."""

    brand_name: str
    kind: str
    age_group: str
    gender: str
    guides: tuple[str, ...]
    updated_at: datetime
    source_url: str
    source_notes: str
    rows: tuple[dict[str, float | int | str], ...]

    def covers(self, guide: str) -> bool:
        """Whether this chart replaces the default for ``guide``.

        A chart with no guides covers every family.
        """
        return not self.guides or guide in self.guides


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
    if chart.kind not in KindSlug:
        raise ValueError(f"Unknown measurement kind {chart.kind!r} on {brand_name!r}.")
    if chart.age_group not in AgeGroup:
        raise ValueError(f"Unknown age group {chart.age_group!r} on {brand_name!r}.")
    if chart.gender not in {"", Gender.MALE, Gender.FEMALE}:
        raise ValueError(f"Unknown chart gender {chart.gender!r} on {brand_name!r}.")
    unknown = [guide for guide in chart.guides if guide not in OVERRIDE_GUIDE_SLUGS]
    if unknown:
        raise ValueError(f"Unknown override guides {unknown!r} on {brand_name!r}.")
    if chart.updated_at.tzinfo is None:
        raise ValueError(
            f"Review date for {brand_name!r} chart {chart.id} must include a timezone."
        )


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


def _read_chart_rows(path: Path) -> tuple[dict[str, float | int | str], ...]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported chart schema in {path.name}.")
    if set(payload) != {"schema_version", "rows"}:
        raise ValueError(f"{path.name} must contain only schema_version and rows.")
    return _parse_rows(path.stem, payload["rows"])


@cache
def _load_brands() -> tuple[tuple[str, tuple[BrandConversionChart, ...]], ...]:
    """``(brand name, charts)`` for every brand in the catalog.

    Names stay in catalog order. A brand whose guide matches the defaults has
    an empty chart tuple. Each override's rows are loaded from its UUID file.
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
            parsed.append(
                BrandConversionChart(
                    brand_name=brand.name,
                    kind=override.kind,
                    age_group=override.age_group,
                    gender=override.gender,
                    guides=override.guides,
                    updated_at=override.updated_at,
                    source_url=override.source_url,
                    source_notes=override.source_notes,
                    rows=_read_chart_rows(path),
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


def charts_for_brand(brand_name: str) -> tuple[BrandConversionChart, ...]:
    """Charts whose brand name matches, case-insensitively."""
    key = brand_name.strip().casefold()
    return tuple(
        chart for chart in load_brand_charts() if chart.brand_name.casefold() == key
    )


def chart_for(
    brand_name: str,
    kind: str,
    age_group: str,
    gender: str,
    guide: str | None = None,
) -> BrandConversionChart | None:
    """Pick a brand chart for this kind, demographic, and optional guide.

    A chart that lists ``guide`` wins over a chart with no guides (one chart for
    every family). When ``guide`` is omitted, a chart for that kind and
    demographic is returned only when there is exactly one. A male or female
    chart wins over a chart with a blank gender (the shared chart for that age
    group).
    """
    age = age_group.strip().lower()
    sex = gender.strip().lower()
    kind_slug = kind.strip().lower()
    candidates = [
        chart
        for chart in charts_for_brand(brand_name)
        if chart.kind == kind_slug
        and chart.age_group == age
        and chart.gender in {sex, ""}
    ]
    if guide:
        explicit = [chart for chart in candidates if guide in chart.guides]
        pool = explicit or [chart for chart in candidates if not chart.guides]
        gendered = [chart for chart in pool if chart.gender == sex]
        candidates = gendered or pool
    elif sex:
        gendered = [chart for chart in candidates if chart.gender == sex]
        if gendered:
            candidates = gendered
    if len(candidates) == 1:
        return candidates[0]
    return None
