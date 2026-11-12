"""List every default chart a size token sits on.

``decode_size_description`` picks one reading once the product type is known.
``chart_hits`` does not. It returns each chart the token could belong to, and
the product families, age groups, and genders of those charts. The caller
stores the hits and intersects the three sets across a line.

A region is read from a prefix on the token (``EU 39``). There is no
``source_region`` argument, and a bare number does not assume UK or a dress
size. An empty set abstains: a letter, or a number on no chart, leaves the
other tokens free to decide. A hit with a blank age or gender adds nothing
to that set.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import cache

from fashion_size.demographics import AgeGroup, Gender
from fashion_size.product_types import ProductTypeFamily
from fashion_size.scales import DEFAULT_SCALES
from fashion_size.size_types import SizeTypeSlug
from fashion_size.types import (
    AGE_MONTHS,
    AGE_MONTHS_SIZE,
    AGE_YEARS,
    AGE_YEARS_SIZE,
    CHART_LOCALES,
    CUP_RANGE,
    CUP_TOKENS,
    LETTER,
    LETTER_SIZE,
    SIZE_TYPE_BY_SLUG,
    ConversionScale,
    Locale,
    SizeFamily,
    SizeType,
    normalize_cup_token,
    normalize_raw,
    size_unit_for_locale,
)

# Even UK dress labels printed on a bra. The same span as feed decoding.
_BRA_DRESS_LOW = 4
_BRA_DRESS_HIGH = 24
_UNPLACED = "unplaced"
_BRAS: frozenset[ProductTypeFamily] = frozenset({ProductTypeFamily.BRAS})
_NO_FAMILIES: frozenset[ProductTypeFamily] = frozenset()
# Trailing fit codes. Single letters are the short forms (``60L``); the words
# are the feed abbreviations. ``S``, ``R``, and ``L`` are cup letters too, so a
# number plus one of those letters is a length, not a band.
_LENGTH = r"SHT|REG|LNG|PET|TAL|[SRLT]"
_REGION = r"UK|EUR|EU|US|AU|FR"
_NUM = r"\d{1,2}(?:\.\d)?"
_CUP_RANGE_TEXT = r"GG\s*[-–]\s*H|A\s*[-–]\s*C|D\s*[-–]\s*E|F\s*[-–]\s*G"
_CUP_LETTER = "|".join(
    sorted(
        (token for token in CUP_TOKENS if token not in {"S", "R", "L"}),
        key=len,
        reverse=True,
    )
)
_LENGTH_KINDS = frozenset(
    {
        SizeTypeSlug.DRESS.value,
        SizeTypeSlug.WAIST_SIZE.value,
        SizeTypeSlug.CHEST_SIZE.value,
    }
)
_KIND_ORDER = {
    kind: index
    for index, kind in enumerate(
        (
            SizeTypeSlug.DRESS.value,
            SizeTypeSlug.WAIST_SIZE.value,
            SizeTypeSlug.CHEST_SIZE.value,
            SizeTypeSlug.ADULT_SHOE.value,
            SizeTypeSlug.KIDS_SHOE.value,
            SizeTypeSlug.BABY_SHOE.value,
            SizeTypeSlug.BAND_SIZE.value,
            SizeTypeSlug.CUP_SIZE.value,
            SizeTypeSlug.CUP_RANGE.value,
            SizeTypeSlug.LETTER.value,
            SizeTypeSlug.AGE_MONTHS.value,
            SizeTypeSlug.AGE_YEARS.value,
            _UNPLACED,
        )
    )
}
_REGION_ORDER = {
    Locale.UK: 0,
    Locale.EU: 1,
    Locale.US: 2,
    Locale.AU: 3,
    Locale.FR: 4,
    None: 5,
}
_AGE_ORDER = {AgeGroup.ADULT: 0, AgeGroup.CHILD: 1, AgeGroup.BABY: 2, None: 3}
_GENDER_ORDER = {Gender.FEMALE: 0, Gender.MALE: 1, None: 2}
_PREFIXES = {
    "UK": Locale.UK,
    "EU": Locale.EU,
    "EUR": Locale.EU,
    "US": Locale.US,
    "AU": Locale.AU,
    "FR": Locale.FR,
}

_NUMBER_CELL = re.compile(
    rf"^(?:(?P<region>{_REGION})\s*[-:]?\s*)?"
    rf"(?P<first>{_NUM})"
    rf"(?:\s*/\s*(?P<second>{_NUM}))?"
    rf"(?:\s*(?P<length>{_LENGTH}))?$",
    re.IGNORECASE,
)
_CUP_RANGE_CELL = re.compile(
    rf"^(?:(?P<region>{_REGION})\s*[-:]?\s*)?"
    rf"(?:(?P<number>{_NUM})\s*)?"
    rf"(?P<range>{_CUP_RANGE_TEXT})$",
    re.IGNORECASE,
)
_CUP_CELL = re.compile(
    rf"^(?:(?P<region>{_REGION})\s*[-:]?\s*)?"
    rf"(?P<number>{_NUM})\s*(?P<cup>{_CUP_LETTER})$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ChartHit:
    """One chart a token sits on, or one label that is not a chart number.

    ``size_kind`` is the size-type slug (``dress``, ``adult-shoe``,
    ``band-size``, ``cup-size``, ``cup-range``, ``letter``, ``age-years``,
    ``age-months``) or ``unplaced`` when the number is on no chart.

    ``families`` is that size type's product affinity, collapsed to families.
    A cup or cup range on the cell replaces every hit's families with bras.
    A bra dress number stays ``size_kind`` ``dress``.

    ``chart_region``, ``age_group``, and ``gender`` are ``None`` when the hit
    has none. ``label`` is a cup, cup range, letter, or age token.
    ``length_token`` is the fit code written on the cell (``reg``, ``l``),
    lowercased, or ``""``.
    """

    size_kind: str
    families: frozenset[ProductTypeFamily]
    chart_region: Locale | None = None
    age_group: AgeGroup | None = None
    gender: Gender | None = None
    number: Decimal | None = None
    length_token: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class ChartHits:
    """Charts for one token, and the potentials a caller intersects.

    ``families``, ``age_groups``, and ``genders`` are the union of ``hits``.
    A blank age or gender on a hit is left out. An empty set abstains.
    """

    families: frozenset[ProductTypeFamily]
    age_groups: frozenset[AgeGroup]
    genders: frozenset[Gender]
    hits: tuple[ChartHit, ...]


def chart_hits(token: str) -> ChartHits:
    """Return every default chart ``token`` sits on, and the potentials.

    ``token`` is one cell (``14 REG``, ``EU 39``, ``10 A-C``, ``58/60L``).
    A prefix (``UK``, ``EU``, ``EUR``, ``US``, ``AU``, ``FR``) keeps that
    region's charts. French dress, shoe, and chest labels use the EU numbers
    and are reported as ``FR``. French waist is not a chart. A French band is
    the EU centimetre label plus 15.

    Hits are ordered by number, then size kind, age, gender, and region.
    """
    if not isinstance(token, str):
        raise TypeError(f"token must be a str, not {type(token).__name__}.")
    text = " ".join(token.strip().split())
    if not text:
        return _collect(())
    for reader in (_letter_hit, _age_hit, _cup_range_hits, _cup_hits, _number_hits):
        found = reader(text)
        if found is not None:
            return _collect(found)
    return _collect(())


def _collect(hits: tuple[ChartHit, ...]) -> ChartHits:
    ordered = tuple(sorted(hits, key=_hit_key))
    return ChartHits(
        families=frozenset(family for hit in ordered for family in hit.families),
        age_groups=frozenset(
            hit.age_group for hit in ordered if hit.age_group is not None
        ),
        genders=frozenset(hit.gender for hit in ordered if hit.gender is not None),
        hits=ordered,
    )


def _hit_key(hit: ChartHit) -> tuple[object, ...]:
    number_rank = (1, Decimal(0)) if hit.number is None else (0, hit.number)
    return (
        number_rank,
        _KIND_ORDER[hit.size_kind],
        _AGE_ORDER[hit.age_group],
        _GENDER_ORDER[hit.gender],
        _REGION_ORDER[hit.chart_region],
        hit.label,
        hit.length_token,
    )


def _letter_hit(text: str) -> tuple[ChartHit, ...] | None:
    if not any(pattern.fullmatch(text) for pattern in LETTER_SIZE.recognition_patterns()):
        return None
    try:
        label = LETTER.normalize_label(text)
    except ValueError:
        return None
    # A letter abstains. Its size type's affinity is not a potential here.
    return (
        ChartHit(size_kind=SizeTypeSlug.LETTER, families=_NO_FAMILIES, label=label),
    )


def _age_hit(text: str) -> tuple[ChartHit, ...] | None:
    recognised = (
        (AGE_MONTHS, AGE_MONTHS_SIZE, AgeGroup.BABY),
        (AGE_YEARS, AGE_YEARS_SIZE, AgeGroup.CHILD),
    )
    for size_type, unit, age_group in recognised:
        if not any(pattern.fullmatch(text) for pattern in unit.recognition_patterns()):
            continue
        try:
            label = size_type.normalize_label(text)
        except ValueError:
            continue
        return (
            ChartHit(
                size_kind=size_type.slug,
                families=_NO_FAMILIES,
                age_group=age_group,
                label=label,
            ),
        )
    return None


def _cup_range_hits(text: str) -> tuple[ChartHit, ...] | None:
    match = _CUP_RANGE_CELL.fullmatch(text)
    if match is None:
        return None
    span = ChartHit(
        size_kind=SizeTypeSlug.CUP_RANGE,
        families=_BRAS,
        label=_cup_range_label(match.group("range")),
    )
    raw_number = match.group("number")
    if raw_number is None:
        return (span,)
    number = normalize_raw(raw_number)
    if _bra_dress_number(number):
        dress = _uk_womens_dress(number)
        hits = (dress, span) if dress is not None else (span,)
        return tuple(replace(hit, families=_BRAS) for hit in hits)
    bands = _band_hits(number, _region(match.group("region")))
    return tuple(replace(hit, families=_BRAS) for hit in (*bands, span))


def _cup_hits(text: str) -> tuple[ChartHit, ...] | None:
    match = _CUP_CELL.fullmatch(text)
    if match is None:
        return None
    number = normalize_raw(match.group("number"))
    cup = ChartHit(
        size_kind=SizeTypeSlug.CUP_SIZE,
        families=_BRAS,
        age_group=AgeGroup.ADULT,
        gender=Gender.FEMALE,
        label=normalize_cup_token(match.group("cup")),
    )
    bands = _band_hits(number, _region(match.group("region")))
    return tuple(replace(hit, families=_BRAS) for hit in (*bands, cup))


def _number_hits(text: str) -> tuple[ChartHit, ...] | None:
    match = _NUMBER_CELL.fullmatch(text)
    if match is None:
        return None
    region = _region(match.group("region"))
    length = (match.group("length") or "").lower()
    found: list[ChartHit] = []
    for raw in (match.group("first"), match.group("second")):
        if raw is None:
            continue
        hits = list(_charts_for_number(normalize_raw(raw), region))
        if length:
            hits = _with_length(hits, length)
        found.extend(hits)
    return tuple(found)


def _band_hits(number: Decimal, region: Locale | None) -> tuple[ChartHit, ...]:
    """Band charts that contain ``number``, or one unplaced hit when none do.

    The dress chart for the same number is not returned. ``30`` and ``32`` are
    on the women's dress chart and are still bands once a cup is written.
    """
    bands = tuple(
        hit
        for hit in _charts_for_number(number, region)
        if hit.size_kind == SizeTypeSlug.BAND_SIZE
    )
    if bands:
        return bands
    return (ChartHit(size_kind=_UNPLACED, families=_NO_FAMILIES, number=number),)


def _with_length(hits: list[ChartHit], token: str) -> list[ChartHit]:
    """Keep adult dress, waist, and chest. Drop shoe, band, and child hits."""
    kept: list[ChartHit] = []
    for hit in hits:
        if hit.size_kind == _UNPLACED:
            kept.append(replace(hit, length_token=token))
            continue
        if hit.size_kind not in _LENGTH_KINDS or hit.age_group is not AgeGroup.ADULT:
            continue
        kept.append(replace(hit, age_group=AgeGroup.ADULT, length_token=token))
    return kept


def _uk_womens_dress(number: Decimal) -> ChartHit | None:
    if number not in _column_numbers(
        SizeTypeSlug.DRESS, AgeGroup.ADULT.value, Gender.FEMALE.value, Locale.UK.value
    ):
        return None
    return ChartHit(
        size_kind=SizeTypeSlug.DRESS,
        families=_BRAS,
        chart_region=Locale.UK,
        age_group=AgeGroup.ADULT,
        gender=Gender.FEMALE,
        number=number,
    )


def _charts_for_number(number: Decimal, region: Locale | None) -> tuple[ChartHit, ...]:
    """One hit per chart column that contains ``number``.

    The kids' shoe rows are stored for babies and for children. They are
    returned once, as children. Baby shoes stay on the baby shoe chart.
    A band chart stored for both adult genders, with the same rows, is one
    hit with a blank gender: one chart for every adult.
    """
    grouped: dict[tuple[object, ...], list[Gender | None]] = {}
    meta: dict[tuple[object, ...], tuple[SizeType, Locale, AgeGroup]] = {}
    for (slug, age, gender), scales in DEFAULT_SCALES.items():
        if slug == SizeTypeSlug.KIDS_SHOE and age == AgeGroup.BABY.value:
            continue
        size_type = SIZE_TYPE_BY_SLUG[slug]
        if size_type.family is SizeFamily.CUP_SIZE:
            continue
        scale = _current(scales)
        for locale in _locales(region, size_type):
            if number not in _column_numbers(slug, age, gender, locale.value):
                continue
            key = (slug, locale, age, scale.rows)
            bucket = grouped.get(key)
            if bucket is None:
                grouped[key] = [_as_gender(gender)]
                meta[key] = (size_type, locale, AgeGroup(age))
            else:
                bucket.append(_as_gender(gender))
    if not grouped:
        return (ChartHit(size_kind=_UNPLACED, families=_NO_FAMILIES, number=number),)
    hits: list[ChartHit] = []
    for key, genders in grouped.items():
        size_type, locale, age_group = meta[key]
        hits.append(
            ChartHit(
                size_kind=size_type.slug,
                families=_affinity_families(size_type),
                chart_region=locale,
                age_group=age_group,
                gender=_shared_gender(genders),
                number=number,
            )
        )
    return tuple(hits)


def _locales(region: Locale | None, size_type: SizeType) -> tuple[Locale, ...]:
    if region is not None:
        return (region,)
    if size_type.family is SizeFamily.BAND_SIZE:
        return (*CHART_LOCALES, Locale.FR)
    return CHART_LOCALES


def _shared_gender(genders: list[Gender | None]) -> Gender | None:
    """The gender when every copy of these rows names it, else blank."""
    concrete = {gender for gender in genders if gender is not None}
    if len(concrete) == 1 and all(gender is not None for gender in genders):
        return next(iter(concrete))
    return None


def _affinity_families(size_type: SizeType) -> frozenset[ProductTypeFamily]:
    return frozenset(product.family for product in size_type.affinity)


def _as_gender(value: str) -> Gender | None:
    if not value:
        return None
    return Gender(value)


def _region(token: str | None) -> Locale | None:
    if not token:
        return None
    return _PREFIXES[token.upper()]


def _cup_range_label(raw: str) -> str:
    return CUP_RANGE.normalize_label(raw.replace("–", "-"))


def _bra_dress_number(number: Decimal) -> bool:
    if number != number.to_integral_value():
        return False
    value = int(number)
    return _BRA_DRESS_LOW <= value <= _BRA_DRESS_HIGH and value % 2 == 0


def _current(scales: tuple[ConversionScale, ...]) -> ConversionScale:
    for scale in scales:
        if scale.effective_until is None:
            return scale
    return scales[-1]


@cache
def _column_numbers(
    slug: str, age: str, gender: str, locale_value: str
) -> frozenset[Decimal]:
    scale = _current(DEFAULT_SCALES[(slug, age, gender)])
    locale = Locale(locale_value)
    family = scale.size_type.family
    if locale is Locale.FR and not (
        family is SizeFamily.BAND_SIZE or family.french_matches_eu
    ):
        return frozenset()
    unit = size_unit_for_locale(scale.size_type, locale)
    return frozenset(
        value for value in scale.raw_values(unit) if isinstance(value, Decimal)
    )
