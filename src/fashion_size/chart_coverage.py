"""Which catalogue age groups each size type's charts may serve.

A **size type** (``kids-shoe``, ``baby-shoe``, …) defines the numeric scale on the
attribute. A **catalogue age group** (``child``, ``baby``, ``adult``) is how the
product is filed. ``CHART_AGE_COVERAGE`` lists, per size type, every catalogue age
that may use that type's conversion charts.

Brand overrides and default scales are stored under a chart ``age_group``. Lookup
tries the product's age first, then any **fallback** ages for that size type (for
example a ``kids-shoe`` chart filed under ``child`` also serves baby-labelled
products).
"""

from __future__ import annotations

from fashion_size.demographics import AgeGroup
from fashion_size.size_types import SizeTypeSlug

# Catalogue age groups that may use conversion charts for each size type.
CHART_AGE_COVERAGE: dict[str, frozenset[AgeGroup]] = {
    SizeTypeSlug.DRESS.value: frozenset({AgeGroup.ADULT, AgeGroup.CHILD}),
    SizeTypeSlug.ADULT_SHOE.value: frozenset({AgeGroup.ADULT}),
    SizeTypeSlug.KIDS_SHOE.value: frozenset({AgeGroup.CHILD, AgeGroup.BABY}),
    SizeTypeSlug.BABY_SHOE.value: frozenset({AgeGroup.BABY}),
    SizeTypeSlug.CUP_SIZE.value: frozenset({AgeGroup.ADULT}),
    SizeTypeSlug.BAND_SIZE.value: frozenset({AgeGroup.ADULT}),
    SizeTypeSlug.WAIST_SIZE.value: frozenset({AgeGroup.ADULT, AgeGroup.CHILD}),
    SizeTypeSlug.CHEST_SIZE.value: frozenset({AgeGroup.ADULT, AgeGroup.CHILD}),
}

# When the product is filed under the key age, try charts stored under these ages
# in order (after validating the product age is in ``CHART_AGE_COVERAGE``).
_CHART_AGE_LOOKUP_ORDER: dict[tuple[str, str], tuple[str, ...]] = {
    (SizeTypeSlug.KIDS_SHOE.value, AgeGroup.BABY.value): (
        AgeGroup.BABY.value,
        AgeGroup.CHILD.value,
    ),
}


def chart_age_groups_for_lookup(
    size_type: str, catalogue_age_group: str
) -> tuple[str, ...]:
    """Chart ``age_group`` values to try for a product, most specific first."""
    slug = size_type.strip().lower()
    age = catalogue_age_group.strip().lower()
    if age not in AgeGroup:
        return (age,)
    coverage = CHART_AGE_COVERAGE.get(slug)
    if coverage is not None and AgeGroup(age) not in coverage:
        return (age,)
    ordered = _CHART_AGE_LOOKUP_ORDER.get((slug, age))
    if ordered is not None:
        return ordered
    return (age,)


def default_chart_age_groups(size_type: str) -> tuple[AgeGroup, ...]:
    """Catalogue ages that carry a shared default chart for ``size_type``.

    Used when one row set is registered once per covered age (blank gender).
    Returns an empty tuple when ``size_type`` is not in ``CHART_AGE_COVERAGE``.
    """
    coverage = CHART_AGE_COVERAGE.get(size_type.strip().lower())
    if coverage is None:
        return ()
    return tuple(sorted(coverage, key=lambda group: group.value))
