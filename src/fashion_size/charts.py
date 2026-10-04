"""Brand conversion charts shipped as JSON.

Each chart records when it was last checked, where it came from, and which
override guides it replaces. Rows are ``{uk, eu, us, au}``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

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


def _parse_updated_at(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("Brand chart is missing updated_at.")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"updated_at must include a timezone: {text!r}.")
    return parsed


def _parse_chart(entry: dict[str, Any]) -> BrandConversionChart:
    brand_name = str(entry.get("brand_name") or "").strip()
    if not brand_name:
        raise ValueError("Brand chart is missing brand_name.")
    kind = str(entry.get("kind") or "")
    if kind not in KindSlug:
        raise ValueError(f"Unknown measurement kind {kind!r} on {brand_name!r}.")
    age_group = str(entry.get("age_group") or "")
    if age_group not in AgeGroup:
        raise ValueError(f"Unknown age group {age_group!r} on {brand_name!r}.")
    gender = str(entry.get("gender") or "")
    if gender not in {"", Gender.MALE, Gender.FEMALE}:
        raise ValueError(f"Unknown chart gender {gender!r} on {brand_name!r}.")
    guides = tuple(str(guide) for guide in entry.get("guides") or [])
    unknown = [guide for guide in guides if guide not in OVERRIDE_GUIDE_SLUGS]
    if unknown:
        raise ValueError(f"Unknown override guides {unknown!r} on {brand_name!r}.")
    rows = entry.get("rows") or []
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{brand_name!r} chart has no rows.")
    normalised_rows: list[dict[str, float | int | str]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"uk", "eu", "us", "au"}:
            raise ValueError(f"{brand_name!r} chart row must have uk, eu, us, and au.")
        normalised: dict[str, float | int | str] = {}
        for key in ("uk", "eu", "us", "au"):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, str | int | float):
                raise ValueError(f"{brand_name!r} chart has an invalid {key} value {value!r}.")
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{brand_name!r} chart has an empty {key} value.")
            normalised[key] = value
        normalised_rows.append(normalised)
    return BrandConversionChart(
        brand_name=brand_name,
        kind=kind,
        age_group=age_group,
        gender=gender,
        guides=guides,
        updated_at=_parse_updated_at(entry.get("updated_at")),
        source_url=str(entry.get("source_url") or ""),
        source_notes=str(entry.get("source_notes") or ""),
        rows=tuple(normalised_rows),
    )


@cache
def load_brand_charts() -> tuple[BrandConversionChart, ...]:
    """Every shipped brand chart, in fixture order.

    The fixture's ``schema_version`` must be ``1``.
    """
    fixture = Path(__file__).resolve().parent / "fixtures" / "brand_conversion_charts.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError(f"Unsupported brand chart schema {payload.get('schema_version')!r}.")
    charts = payload.get("charts")
    if not isinstance(charts, list) or not charts:
        raise ValueError("Brand chart fixture has no charts.")
    return tuple(_parse_chart(entry) for entry in charts)


def charts_for_brand(brand_name: str) -> tuple[BrandConversionChart, ...]:
    """Charts whose brand name matches, case-insensitively."""
    key = brand_name.strip().casefold()
    return tuple(chart for chart in load_brand_charts() if chart.brand_name.casefold() == key)


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
        if chart.kind == kind_slug and chart.age_group == age and chart.gender in {sex, ""}
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
