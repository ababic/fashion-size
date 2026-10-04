"""In-memory measurement types: families, kinds, and kind-specific measurements.

Each measurement is a concrete entity such as ``UK_DRESS_SIZE`` or
``CM_CHEST_SIZE`` — it knows its kind and its locale (``universal`` for
centimetres and inches). Default conversion charts live in
``fashion_size.scales``. Brand-specific charts are JSON rows named by id — see
``fashion_size.charts``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any

from fashion_size.demographics import (
    DEMOGRAPHIC_LABELS,
    AgeGroup,
    Gender,
    age_group_label,
    gender_label,
)
from fashion_size.kinds import KindSlug


class MeasurementFamily(StrEnum):
    """Groups of measurement kinds that convert the same way."""

    LENGTH = "length"
    DRESS_SIZE = "dress_size"
    SHOE_SIZE = "shoe_size"
    CUP_SIZE = "cup_size"
    BAND_SIZE = "band_size"
    WAIST_SIZE = "waist_size"
    CHEST_SIZE = "chest_size"

    @property
    def supports_brand_overrides(self) -> bool:
        """Locale charts can be replaced per brand.

        Length uses a formula. Band size always uses the default chart.
        """
        return self not in {MeasurementFamily.LENGTH, MeasurementFamily.BAND_SIZE}

    @property
    def french_matches_eu(self) -> bool:
        """French dress, shoe, cup, and chest-size labels are the EU measurement.

        Waist size is not: French swim and trouser charts use a different number.
        Band size is not either: a French band is the EU centimetre label plus 15.
        """
        return self in {
            MeasurementFamily.DRESS_SIZE,
            MeasurementFamily.SHOE_SIZE,
            MeasurementFamily.CUP_SIZE,
            MeasurementFamily.CHEST_SIZE,
        }


class Locale(StrEnum):
    """Regional size system, or ``universal`` for centimetres / inches."""

    UNIVERSAL = "universal"
    UK = "uk"
    EU = "eu"
    US = "us"
    AU = "au"
    FR = "fr"


# Chart columns. French is not a column: dress, shoe, and cup sizes use the EU measurement.
# French band size is the EU centimetre label plus this offset (EU 75 = FR 90).
CHART_LOCALES: tuple[Locale, ...] = (Locale.UK, Locale.EU, Locale.US, Locale.AU)
FRENCH_BAND_OFFSET = Decimal(15)


class IncompatibleMeasurementError(ValueError):
    """Source and target measurements are not convertible for this kind."""


class UnknownSizeError(ValueError):
    """The raw value is not on the conversion chart for this kind and demographic."""


class MissingScaleError(ValueError):
    """No default (or brand) chart exists for this kind and demographic."""


class LengthOutOfRangeError(ValueError):
    """Length is outside the clothing / accessories / curtain range (5–150 inches)."""


def _finite_decimal(value: int | float | str | Decimal) -> Decimal:
    """Parse a measurement number. ``inf`` and ``nan`` are not sizes."""
    raw = value if isinstance(value, Decimal) else Decimal(str(value))
    if not raw.is_finite():
        raise ValueError(f"Non-finite measurement {value!r}")
    return raw


def normalize_raw(value: int | float | str | Decimal) -> Decimal:
    """Canonical chart size: one decimal place, whole numbers stored as integers."""
    raw = _finite_decimal(value)
    quantized = raw.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if quantized == quantized.to_integral():
        return Decimal(int(quantized))
    return quantized


def normalize_length_raw(value: int | float | str | Decimal) -> Decimal:
    """Exact centimetre or inch value. Whole numbers are stored as integers.

    Display rounding (nearest centimetre, nearest half inch) is separate.
    """
    raw = _finite_decimal(value)
    if raw == raw.to_integral():
        return Decimal(int(raw))
    return raw


def round_length_for_display(raw: Decimal | int | float | str, unit: str) -> Decimal:
    """Nearest whole centimetre, or nearest half inch, for a displayed length."""
    number = raw if isinstance(raw, Decimal) else Decimal(str(raw))
    if unit == "cm":
        return Decimal(int(number.to_integral_value(rounding=ROUND_HALF_UP)))
    if unit == "in":
        inches = (number * 2).to_integral_value(rounding=ROUND_HALF_UP) / 2
        if inches == inches.to_integral():
            return Decimal(int(inches))
        return inches
    raise ValueError(f"Unknown length unit {unit!r}")


# Cup letters that appear on a UK, EU, US, or AU chart. Ranges such as ``D-E`` are not a size.
CUP_TOKENS: frozenset[str] = frozenset(
    {
        "AA",
        "A",
        "B",
        "C",
        "D",
        "DD",
        "DDD",
        "E",
        "F",
        "FF",
        "G",
        "GG",
        "H",
        "HH",
        "I",
        "J",
        "JJ",
        "K",
        "L",
        "M",
        "N",
        "O",
    }
)


def normalize_cup_token(value: object) -> str:
    """Canonical cup-size letter (``dd`` → ``DD``). Rejects ranges and unknown letters."""
    token = str(value or "").strip().upper().replace(" ", "")
    if token not in CUP_TOKENS:
        raise ValueError(f"Unknown cup size {value!r}.")
    return token


def format_raw(value: int | float | str | Decimal) -> str:
    """Display a raw size without trailing zeros (``7.5``, ``10``)."""
    raw = normalize_raw(value)
    if raw == raw.to_integral():
        return str(int(raw))
    return format(raw.normalize(), "f")


DisplayLanguageGetter = Callable[[], str | None]

_display_language: DisplayLanguageGetter | None = None


def register_display_language(getter: DisplayLanguageGetter) -> None:
    """Use ``getter`` when a caller does not pass a display language.

    The warehouse registers Django's ``get_language``. With no getter, display
    falls back to ``en-gb``.
    """
    global _display_language
    _display_language = getter


def active_display_language() -> str | None:
    """Language code from the registered getter, or ``None`` when unset."""
    if _display_language is None:
        return None
    return _display_language()


def resolve_display_language(locale: str | None = None) -> str:
    """Normalise an explicit language code, the registered getter, or ``en-gb``."""
    language = (locale or active_display_language() or "en-gb").replace("_", "-").strip().lower()
    return language or "en-gb"


def uses_inch_quote(locale: str | None = None) -> bool:
    """English locales typically mark inches with ``"``; others prefer `` in``."""
    language = resolve_display_language(locale)
    return language == "en" or language.startswith("en-")


def format_length_for_language(raw: Decimal | int | float | str, unit: str, locale: str | None = None) -> str:
    """Localise a centimetre or inch value for a language code such as ``en-gb`` or ``de``.

    The stored value stays exact. Display rounds centimetres to the nearest
    whole centimetre and inches to the nearest half inch.
    """
    number = format_raw(round_length_for_display(raw, unit))
    if unit == "in":
        if uses_inch_quote(locale):
            return f'{number}"'
        return f"{number} in"
    if unit == "cm":
        if uses_inch_quote(locale):
            return f"{number}cm"
        return f"{number} cm"
    raise ValueError(f"Unknown length unit {unit!r}")


def resolve_age_gender(age_group: AgeGroup | str, gender: Gender | str) -> tuple[str, str]:
    """Normalise an ``AgeGroup`` × ``Gender`` pair to ``(age_group, gender)`` values.

    This is the same pair used on catalogue items (``adult`` / ``child`` / ``baby``
    with ``male`` / ``female`` / ``unisex``). Unisex adults and children are valid
    pairs; whether a chart exists for them is decided by the scale lookup.
    """
    age = age_group.value if isinstance(age_group, AgeGroup) else str(age_group or "").strip().lower()
    sex = gender.value if isinstance(gender, Gender) else str(gender or "").strip().lower()
    if age not in AgeGroup:
        raise ValueError(f"Unknown age group {age_group!r}.")
    if sex not in Gender:
        raise ValueError(f"Unknown gender {gender!r}.")
    return age, sex


# Blank gender on a chart: one chart for every gender in that age group.
# Not a unisex chart — unisex products use the male chart.
CHART_FOR_ALL_GENDERS = ""
_AGE_GROUPS_WITH_SHARED_CHART = frozenset({AgeGroup.CHILD, AgeGroup.BABY})


def chart_genders(age_group: str, gender: str) -> tuple[str, ...]:
    """Chart genders to try, most specific first.

    A product labelled unisex uses the male chart. There is no unisex chart.

    Children and babies then fall back to the age group's shared chart (blank
    gender): one chart for all kids, or a baby-shoe chart that is not gendered.
    A male or female chart wins when the brand has saved one. Adults do not
    fall back to another gender.
    """
    if gender == Gender.UNISEX:
        gender = Gender.MALE
    if age_group in _AGE_GROUPS_WITH_SHARED_CHART:
        return (gender, CHART_FOR_ALL_GENDERS)
    return (gender,)


def format_age_gender(age_group: str, gender: str) -> str:
    """Display label for an age group and gender.

    Uses ``catalog.constants.Demographic`` (Men, Women, Unisex Kids, …) when the
    pair is one of the usual nine slots. A blank gender is the shared chart for
    that age group (all children, or all babies) — not a unisex chart.
    """
    if not gender:
        if age_group == AgeGroup.CHILD:
            return "All children"
        if age_group == AgeGroup.BABY:
            return "All babies"
        return f"{age_group_label(age_group)} / all genders"
    label = DEMOGRAPHIC_LABELS.get((age_group, gender))
    if label:
        return label
    return f"{age_group_label(age_group)} / {gender_label(gender)}"


@dataclass(frozen=True, slots=True)
class MeasurementKind:
    """Fine-grained size category (dress, adult shoe, chest, …).

    Adult / kids / baby shoes are separate kinds — UK 7 adult is not UK 7 kids.
    """

    slug: str
    family: MeasurementFamily
    label: str
    attribute_slugs: tuple[str, ...] = ()
    # Measurement slug stem when it must not also be an attribute-slug alias.
    # ``uk-waist-size`` is the regional label; ``waist-size`` stays the length kind.
    slug_stem: str = ""

    @property
    def supports_brand_overrides(self) -> bool:
        return self.family.supports_brand_overrides

    def __str__(self) -> str:
        return self.label


DRESS = MeasurementKind(
    KindSlug.DRESS,
    MeasurementFamily.DRESS_SIZE,
    "Dress size",
    ("dress-size",),
)
ADULT_SHOE = MeasurementKind(
    KindSlug.ADULT_SHOE,
    MeasurementFamily.SHOE_SIZE,
    "Adult shoe size",
    ("adult-shoe-size", "shoe-size", "european-shoe-size"),
)
KIDS_SHOE = MeasurementKind(
    KindSlug.KIDS_SHOE,
    MeasurementFamily.SHOE_SIZE,
    "Kids shoe size",
    ("kids-shoe-size",),
)
BABY_SHOE = MeasurementKind(
    KindSlug.BABY_SHOE,
    MeasurementFamily.SHOE_SIZE,
    "Baby shoe size",
    ("baby-shoe-size",),
)
CUP_SIZE = MeasurementKind(
    KindSlug.CUP_SIZE,
    MeasurementFamily.CUP_SIZE,
    "Cup size",
    ("cup-size", "bra-cup", "bra-cup-size"),
)
# Underbust band. Distinct from chest size (a jacket label) and from cup size.
BAND_SIZE = MeasurementKind(
    KindSlug.BAND_SIZE,
    MeasurementFamily.BAND_SIZE,
    "Band size",
    ("bra-band-size",),
    slug_stem="band-size",
)
# Regional garment labels. UK/US/AU are the inch number; EU/IT is a different number.
# Distinct from the length kinds, which only convert centimetres and inches.
WAIST_SIZE = MeasurementKind(
    KindSlug.WAIST_SIZE,
    MeasurementFamily.WAIST_SIZE,
    "Waist size",
    slug_stem="waist-size",
)
CHEST_SIZE = MeasurementKind(
    KindSlug.CHEST_SIZE,
    MeasurementFamily.CHEST_SIZE,
    "Chest size",
    slug_stem="chest-size",
)
CHEST = MeasurementKind(KindSlug.CHEST, MeasurementFamily.LENGTH, "Chest", ("chest-size",))
WAIST = MeasurementKind(KindSlug.WAIST, MeasurementFamily.LENGTH, "Waist", ("waist-size",))
INSIDE_LEG = MeasurementKind(
    KindSlug.INSIDE_LEG,
    MeasurementFamily.LENGTH,
    "Inside leg",
    ("inside-leg", "leg-length"),
)
COLLAR = MeasurementKind(KindSlug.COLLAR, MeasurementFamily.LENGTH, "Collar", ("collar-size",))

MEASUREMENT_KINDS: tuple[MeasurementKind, ...] = (
    DRESS,
    ADULT_SHOE,
    KIDS_SHOE,
    BABY_SHOE,
    CUP_SIZE,
    BAND_SIZE,
    WAIST_SIZE,
    CHEST_SIZE,
    CHEST,
    WAIST,
    INSIDE_LEG,
    COLLAR,
)
MEASUREMENT_KIND_BY_SLUG: dict[str, MeasurementKind] = {kind.slug: kind for kind in MEASUREMENT_KINDS}
BRAND_OVERRIDE_KIND_SLUGS: frozenset[str] = frozenset(
    kind.slug for kind in MEASUREMENT_KINDS if kind.supports_brand_overrides
)
ATTRIBUTE_MEASUREMENT_KINDS: dict[str, MeasurementKind] = {
    slug: kind for kind in MEASUREMENT_KINDS for slug in kind.attribute_slugs
}


@dataclass(frozen=True, slots=True)
class Measurement:
    """A concrete size expression bound to one kind.

    Examples: ``UK_DRESS_SIZE``, ``EU_ADULT_SHOE_SIZE``, ``CM_CHEST_SIZE``.
    Locale is ``universal`` for centimetres and inches; otherwise UK / EU / US / AU.
    """

    slug: str
    kind: MeasurementKind
    locale: Locale
    label: str
    display_suffix: str = ""
    display_prefix: str = ""
    length_unit: str | None = None

    @property
    def supports_brand_overrides(self) -> bool:
        return self.kind.supports_brand_overrides

    def can_convert_to(self, other: Measurement) -> bool:
        return self.kind.slug == other.kind.slug

    def __str__(self) -> str:
        return self.label


def _locale_measurement(kind: MeasurementKind, locale: Locale) -> Measurement:
    attribute = kind.slug_stem or kind.attribute_slugs[0]
    # Cup sizes display as the letter alone (``DD``). Dress and shoe sizes keep a region prefix.
    prefix = "" if kind.family == MeasurementFamily.CUP_SIZE else f"{locale.value.upper()} "
    return Measurement(
        slug=f"{locale.value}-{attribute}",
        kind=kind,
        locale=locale,
        label=f"{locale.value.upper()} {kind.label}",
        display_prefix=prefix,
    )


def _length_measurement(kind: MeasurementKind, *, unit: str, display_suffix: str, label_unit: str) -> Measurement:
    attribute = kind.attribute_slugs[0]
    return Measurement(
        slug=f"{unit}-{attribute}",
        kind=kind,
        locale=Locale.UNIVERSAL,
        label=f"{kind.label} ({label_unit})",
        display_suffix=display_suffix,
        length_unit=unit,
    )


UK_DRESS_SIZE = _locale_measurement(DRESS, Locale.UK)
EU_DRESS_SIZE = _locale_measurement(DRESS, Locale.EU)
US_DRESS_SIZE = _locale_measurement(DRESS, Locale.US)
AU_DRESS_SIZE = _locale_measurement(DRESS, Locale.AU)

UK_ADULT_SHOE_SIZE = _locale_measurement(ADULT_SHOE, Locale.UK)
EU_ADULT_SHOE_SIZE = _locale_measurement(ADULT_SHOE, Locale.EU)
US_ADULT_SHOE_SIZE = _locale_measurement(ADULT_SHOE, Locale.US)
AU_ADULT_SHOE_SIZE = _locale_measurement(ADULT_SHOE, Locale.AU)

UK_KIDS_SHOE_SIZE = _locale_measurement(KIDS_SHOE, Locale.UK)
EU_KIDS_SHOE_SIZE = _locale_measurement(KIDS_SHOE, Locale.EU)
US_KIDS_SHOE_SIZE = _locale_measurement(KIDS_SHOE, Locale.US)
AU_KIDS_SHOE_SIZE = _locale_measurement(KIDS_SHOE, Locale.AU)

UK_BABY_SHOE_SIZE = _locale_measurement(BABY_SHOE, Locale.UK)
EU_BABY_SHOE_SIZE = _locale_measurement(BABY_SHOE, Locale.EU)
US_BABY_SHOE_SIZE = _locale_measurement(BABY_SHOE, Locale.US)
AU_BABY_SHOE_SIZE = _locale_measurement(BABY_SHOE, Locale.AU)

UK_CUP_SIZE = _locale_measurement(CUP_SIZE, Locale.UK)
EU_CUP_SIZE = _locale_measurement(CUP_SIZE, Locale.EU)
US_CUP_SIZE = _locale_measurement(CUP_SIZE, Locale.US)
AU_CUP_SIZE = _locale_measurement(CUP_SIZE, Locale.AU)

UK_BAND_SIZE = _locale_measurement(BAND_SIZE, Locale.UK)
EU_BAND_SIZE = _locale_measurement(BAND_SIZE, Locale.EU)
US_BAND_SIZE = _locale_measurement(BAND_SIZE, Locale.US)
AU_BAND_SIZE = _locale_measurement(BAND_SIZE, Locale.AU)
# French band is its own label (EU centimetres + 15), not an alias of EU.
FR_BAND_SIZE = _locale_measurement(BAND_SIZE, Locale.FR)

# French dress, shoe, and cup sizes are the EU measurement.
FR_DRESS_SIZE = EU_DRESS_SIZE
FR_ADULT_SHOE_SIZE = EU_ADULT_SHOE_SIZE
FR_KIDS_SHOE_SIZE = EU_KIDS_SHOE_SIZE
FR_BABY_SHOE_SIZE = EU_BABY_SHOE_SIZE
FR_CUP_SIZE = EU_CUP_SIZE

UK_WAIST_SIZE = _locale_measurement(WAIST_SIZE, Locale.UK)
EU_WAIST_SIZE = _locale_measurement(WAIST_SIZE, Locale.EU)
US_WAIST_SIZE = _locale_measurement(WAIST_SIZE, Locale.US)
AU_WAIST_SIZE = _locale_measurement(WAIST_SIZE, Locale.AU)

UK_CHEST_SIZE = _locale_measurement(CHEST_SIZE, Locale.UK)
EU_CHEST_SIZE = _locale_measurement(CHEST_SIZE, Locale.EU)
US_CHEST_SIZE = _locale_measurement(CHEST_SIZE, Locale.US)
AU_CHEST_SIZE = _locale_measurement(CHEST_SIZE, Locale.AU)
# French chest-size labels match EU. French waist size does not.
FR_CHEST_SIZE = EU_CHEST_SIZE

INCH_CHEST_SIZE = _length_measurement(CHEST, unit="in", display_suffix='"', label_unit="inches")
CM_CHEST_SIZE = _length_measurement(CHEST, unit="cm", display_suffix="cm", label_unit="centimetres")
INCH_WAIST_SIZE = _length_measurement(WAIST, unit="in", display_suffix='"', label_unit="inches")
CM_WAIST_SIZE = _length_measurement(WAIST, unit="cm", display_suffix="cm", label_unit="centimetres")
INCH_INSIDE_LEG = _length_measurement(INSIDE_LEG, unit="in", display_suffix='"', label_unit="inches")
CM_INSIDE_LEG = _length_measurement(INSIDE_LEG, unit="cm", display_suffix="cm", label_unit="centimetres")
INCH_COLLAR_SIZE = _length_measurement(COLLAR, unit="in", display_suffix='"', label_unit="inches")
CM_COLLAR_SIZE = _length_measurement(COLLAR, unit="cm", display_suffix="cm", label_unit="centimetres")

MEASUREMENTS: tuple[Measurement, ...] = (
    UK_DRESS_SIZE,
    EU_DRESS_SIZE,
    US_DRESS_SIZE,
    AU_DRESS_SIZE,
    UK_ADULT_SHOE_SIZE,
    EU_ADULT_SHOE_SIZE,
    US_ADULT_SHOE_SIZE,
    AU_ADULT_SHOE_SIZE,
    UK_KIDS_SHOE_SIZE,
    EU_KIDS_SHOE_SIZE,
    US_KIDS_SHOE_SIZE,
    AU_KIDS_SHOE_SIZE,
    UK_BABY_SHOE_SIZE,
    EU_BABY_SHOE_SIZE,
    US_BABY_SHOE_SIZE,
    AU_BABY_SHOE_SIZE,
    UK_CUP_SIZE,
    EU_CUP_SIZE,
    US_CUP_SIZE,
    AU_CUP_SIZE,
    UK_BAND_SIZE,
    EU_BAND_SIZE,
    US_BAND_SIZE,
    AU_BAND_SIZE,
    FR_BAND_SIZE,
    UK_WAIST_SIZE,
    EU_WAIST_SIZE,
    US_WAIST_SIZE,
    AU_WAIST_SIZE,
    UK_CHEST_SIZE,
    EU_CHEST_SIZE,
    US_CHEST_SIZE,
    AU_CHEST_SIZE,
    INCH_CHEST_SIZE,
    CM_CHEST_SIZE,
    INCH_WAIST_SIZE,
    CM_WAIST_SIZE,
    INCH_INSIDE_LEG,
    CM_INSIDE_LEG,
    INCH_COLLAR_SIZE,
    CM_COLLAR_SIZE,
)
MEASUREMENT_BY_SLUG: dict[str, Measurement] = {measurement.slug: measurement for measurement in MEASUREMENTS}
for _measurement in MEASUREMENTS:
    if _measurement.locale is Locale.EU and _measurement.kind.family.french_matches_eu:
        MEASUREMENT_BY_SLUG["fr-" + _measurement.slug.removeprefix("eu-")] = _measurement


def resolve_locale(value: Locale | str) -> Locale:
    """Accept a ``Locale`` enum or a slug such as ``uk`` / ``eu``."""
    if isinstance(value, Locale):
        return value
    normalized = str(value or "").strip().lower().replace("_", "-")
    try:
        return Locale(normalized)
    except ValueError as exc:
        raise ValueError(f"Unknown measurement locale {value!r}") from exc


def measurement_for_kind_locale(kind: MeasurementKind, locale: Locale | str) -> Measurement:
    """Return the kind-specific measurement for a chart locale (``uk``, ``eu``, …).

    Length kinds use ``universal`` for both centimetres and inches, so pass a
    concrete ``Measurement`` (or use ``measurement_for_kind_unit``) instead.
    """
    if kind.family == MeasurementFamily.LENGTH:
        raise IncompatibleMeasurementError(
            f"Cannot convert {kind.label} to a chart locale — only centimetres and inches apply."
        )
    resolved = resolve_locale(locale)
    if resolved is Locale.FR and kind.family.french_matches_eu:
        resolved = Locale.EU
    if resolved is Locale.UNIVERSAL:
        raise IncompatibleMeasurementError(
            f"Cannot convert {kind.label} to centimetres or inches — only UK/EU/US/AU locales apply."
        )
    matches = tuple(m for m in MEASUREMENTS if m.kind.slug == kind.slug and m.locale is resolved)
    if not matches:
        raise ValueError(f"No {kind.label} measurement for locale {resolved.value!r}.")
    if len(matches) > 1:
        raise ValueError(
            f"{kind.label} has multiple measurements for locale {resolved.value!r}; "
            "pass a concrete Measurement (e.g. centimetres or inches)."
        )
    return matches[0]


def measurement_for_kind_unit(kind: MeasurementKind, unit: str) -> Measurement:
    """Return the kind-specific centimetre or inch measurement."""
    if kind.family != MeasurementFamily.LENGTH:
        raise IncompatibleMeasurementError(
            f"Cannot convert {kind.label} to centimetres or inches — only UK/EU/US/AU locales apply."
        )
    normalized = str(unit or "").strip().lower()
    if normalized in {"in", "inch", "inches", '"'}:
        normalized = "in"
    elif normalized in {"cm", "centimetre", "centimetres", "centimeter", "centimeters"}:
        normalized = "cm"
    else:
        raise ValueError(f"Unknown length unit {unit!r}.")
    for measurement in MEASUREMENTS:
        if measurement.kind.slug == kind.slug and measurement.length_unit == normalized:
            return measurement
    raise ValueError(f"No {kind.label} measurement for unit {normalized!r}.")


def resolve_target_measurement(kind: MeasurementKind, target: Measurement | Locale | str) -> Measurement:
    """Resolve a convert target: a ``Measurement``, chart locale, or length unit.

    Length kinds only accept ``cm`` / ``in`` (or a concrete length ``Measurement``).
    Chart kinds accept UK / EU / US / AU / FR. French dress, shoe, cup, and chest sizes
    are the EU measurement. French waist size is not. French band size is the EU
    centimetre label plus 15. Cross-kind targets raise
    ``IncompatibleMeasurementError``.
    """
    if isinstance(target, Measurement):
        if target.kind.slug != kind.slug:
            raise IncompatibleMeasurementError(
                f"Cannot convert {kind.label} to {target.label} — measurements must share a kind."
            )
        return target
    if isinstance(target, Locale):
        return measurement_for_kind_locale(kind, target)
    normalized = str(target or "").strip().lower()
    if normalized in {"uk", "eu", "us", "au", "fr", "universal"}:
        return measurement_for_kind_locale(kind, normalized)
    if normalized in {"cm", "centimetre", "centimetres", "centimeter", "centimeters", "in", "inch", "inches", '"'}:
        return measurement_for_kind_unit(kind, normalized)
    return measurement_for_kind_locale(kind, target)


def measurement_kind_for_attribute(attribute_slug: str) -> MeasurementKind | None:
    """Return the measurement kind bound to a catalog attribute slug, if any."""
    key = (attribute_slug or "").strip()
    if key in MEASUREMENT_BY_SLUG:
        return MEASUREMENT_BY_SLUG[key].kind
    return ATTRIBUTE_MEASUREMENT_KINDS.get(key)


def parse_measurement_slug(slug: str) -> Measurement:
    """Return the measurement for a slug such as ``uk-dress-size``."""
    key = (slug or "").strip().lower()
    try:
        return MEASUREMENT_BY_SLUG[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown measurement {slug!r}. Expected a slug such as 'uk-dress-size' or 'cm-chest-size'."
        ) from exc


def measurement_choices() -> list[tuple[str, str]]:
    """``(slug, label)`` pairs for every measurement — usable as model field ``choices``."""
    return [(measurement.slug, measurement.label) for measurement in MEASUREMENTS]


def measurement_choices_for_kind(kind_slug: str) -> list[tuple[str, str]]:
    """``(slug, label)`` pairs for the measurements on one kind (empty when no kind)."""
    key = (kind_slug or "").strip().lower()
    if not key:
        return []
    return [(measurement.slug, measurement.label) for measurement in MEASUREMENTS if measurement.kind.slug == key]


def measurement_value_from_attribute_option(
    slug: str,
    value: str,
    *,
    raw_value_prefix: str = "",
    raw_value_suffix: str = "",
) -> MeasurementValue | None:
    """Build a ``MeasurementValue`` from an AttributeValue's measurement slug and text.

    ``slug`` is the measurement slug stored on the AttributeValue (e.g.
    ``uk-dress-size``). ``value`` is the stored option text (``10``, ``UK 10``,
    ``32"``, …). Affixes are stripped using the attribute's ``raw_value_prefix``
    / ``raw_value_suffix`` when set, otherwise the measurement's display
    prefix/suffix. Returns ``None`` when the slug is not a known measurement or
    the value is not numeric.
    """
    measurement = MEASUREMENT_BY_SLUG.get((slug or "").strip().lower())
    if measurement is None:
        return None
    text = (value or "").strip()
    prefix = raw_value_prefix if raw_value_prefix.strip() else measurement.display_prefix
    suffix = raw_value_suffix if raw_value_suffix.strip() else measurement.display_suffix
    if prefix and text.upper().startswith(prefix.upper()):
        text = text[len(prefix) :].strip()
    if suffix and text.endswith(suffix):
        text = text[: -len(suffix)].strip()
    if not text:
        return None
    try:
        if measurement.kind.family == MeasurementFamily.CUP_SIZE:
            return MeasurementValue(raw=normalize_cup_token(text), measurement=measurement)
        if measurement.kind.family == MeasurementFamily.LENGTH:
            return MeasurementValue(raw=normalize_length_raw(text), measurement=measurement)
        return MeasurementValue(raw=normalize_raw(text), measurement=measurement)
    except (InvalidOperation, ValueError, TypeError):
        return None


def measurement_kind_from_slug(slug: str) -> MeasurementKind:
    try:
        return MEASUREMENT_KIND_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"Unknown measurement kind {slug!r}") from exc


@dataclass(frozen=True, slots=True)
class LocaleSizeRow:
    """One complete size across UK / EU / US / AU."""

    uk: Decimal
    eu: Decimal
    us: Decimal
    au: Decimal

    @classmethod
    def from_numbers(
        cls,
        uk: int | float | str | Decimal,
        eu: int | float | str | Decimal,
        us: int | float | str | Decimal,
        au: int | float | str | Decimal,
    ) -> LocaleSizeRow:
        return cls(
            uk=normalize_raw(uk),
            eu=normalize_raw(eu),
            us=normalize_raw(us),
            au=normalize_raw(au),
        )

    def value_for(self, locale: Locale | str) -> Decimal:
        slug = locale.value if isinstance(locale, Locale) else locale.strip().lower()
        if slug not in {"uk", "eu", "us", "au"}:
            raise KeyError(locale)
        return getattr(self, slug)

    def as_dict(self) -> dict[str, float | int]:
        values: dict[str, float | int] = {}
        for slug in ("uk", "eu", "us", "au"):
            raw = getattr(self, slug)
            values[slug] = int(raw) if raw == raw.to_integral() else float(raw)
        return values


@dataclass(frozen=True, slots=True)
class LetterSizeRow:
    """One cup size across UK / EU / US / AU (letters, not numbers)."""

    uk: str
    eu: str
    us: str
    au: str

    @classmethod
    def from_tokens(cls, uk: object, eu: object, us: object, au: object) -> LetterSizeRow:
        return cls(
            uk=normalize_cup_token(uk),
            eu=normalize_cup_token(eu),
            us=normalize_cup_token(us),
            au=normalize_cup_token(au),
        )

    def value_for(self, locale: Locale | str) -> str:
        slug = locale.value if isinstance(locale, Locale) else locale.strip().lower()
        if slug not in {"uk", "eu", "us", "au"}:
            raise KeyError(locale)
        return getattr(self, slug)

    def as_dict(self) -> dict[str, str]:
        return {"uk": self.uk, "eu": self.eu, "us": self.us, "au": self.au}


@dataclass(frozen=True, slots=True)
class ConversionScale:
    """A complete value set for one kind and one age-group × gender pair."""

    kind: MeasurementKind
    age_group: str
    gender: str
    rows: tuple[LocaleSizeRow, ...] | tuple[LetterSizeRow, ...]

    def _chart_locale_and_needle(
        self,
        raw: int | float | str | Decimal,
        measurement: Measurement,
    ) -> tuple[Locale, Decimal | str]:
        """Column and value to look up. French band labels sit 15 above the EU column."""
        if self.kind.family == MeasurementFamily.CUP_SIZE:
            return measurement.locale, normalize_cup_token(raw)
        number = normalize_raw(raw)
        if self.kind.family is MeasurementFamily.BAND_SIZE and measurement.locale is Locale.FR:
            return Locale.EU, number - FRENCH_BAND_OFFSET
        return measurement.locale, number

    def _value_for_measurement(self, row: LocaleSizeRow | LetterSizeRow, measurement: Measurement) -> Decimal | str:
        if self.kind.family is MeasurementFamily.BAND_SIZE and measurement.locale is Locale.FR:
            return normalize_raw(row.value_for(Locale.EU)) + FRENCH_BAND_OFFSET
        return row.value_for(measurement.locale)

    def raw_values(self, measurement: Measurement) -> tuple[Decimal, ...] | tuple[str, ...]:
        """All stored raw values for one locale — the attribute's value set in that locale."""
        return tuple(self._value_for_measurement(row, measurement) for row in self.rows)

    def row_for(self, raw: int | float | str | Decimal, measurement: Measurement) -> LocaleSizeRow | LetterSizeRow:
        locale, needle = self._chart_locale_and_needle(raw, measurement)
        for row in self.rows:
            if row.value_for(locale) == needle:
                return row
        if self.kind.family == MeasurementFamily.CUP_SIZE:
            shown = needle if isinstance(needle, str) else format_raw(needle)
        else:
            shown = format_raw(normalize_raw(raw))
        raise UnknownSizeError(
            f"{self.kind.label} {shown} ({measurement.label}) is not on the "
            f"{format_age_gender(self.age_group, self.gender)} conversion chart."
        )

    def convert_raw(
        self,
        raw: int | float | str | Decimal,
        source: Measurement,
        target: Measurement,
    ) -> Decimal | str:
        if source == target:
            if self.kind.family == MeasurementFamily.CUP_SIZE:
                return normalize_cup_token(raw)
            return normalize_raw(raw)
        return self._value_for_measurement(self.row_for(raw, source), target)


@dataclass(frozen=True, slots=True)
class MeasurementValue:
    """A raw size stored in a concrete measurement (which already knows its kind).

    Numeric kinds store a ``Decimal``. Cup size stores the letter for that
    locale (``DD``, ``E``, ``DDD``).
    """

    raw: Decimal | str
    measurement: Measurement

    def __post_init__(self) -> None:
        if self.measurement.kind.family == MeasurementFamily.CUP_SIZE:
            object.__setattr__(self, "raw", normalize_cup_token(self.raw))
        elif self.measurement.kind.family == MeasurementFamily.LENGTH:
            object.__setattr__(self, "raw", normalize_length_raw(self.raw))
        else:
            object.__setattr__(self, "raw", normalize_raw(self.raw))

    @property
    def kind(self) -> MeasurementKind:
        return self.measurement.kind

    @classmethod
    def from_raw(cls, raw: int | float | str | Decimal, measurement: Measurement) -> MeasurementValue:
        return cls(raw=raw, measurement=measurement)

    def display(self) -> str:
        """Canonical format (English / UK conventions: ``32"``, ``81cm``, ``UK 10``, ``DD``)."""
        return self.localised_display("en-gb")

    def localised_display(self, locale: str | None = None) -> str:
        """Format for a Django language code (or the active language when omitted).

        Inches use a quote mark in English locales (``32"``) and a spaced `` in``
        suffix elsewhere (``32 in``). Centimetres omit the space in English
        (``81cm``) and include it otherwise (``81 cm``). Length display rounds
        to the nearest centimetre or half inch; ``raw`` stays exact. Dress and
        shoe sizes keep their UK / EU / US / AU prefix. Cup sizes are the letter
        alone (``A``, ``DD``), in every language.
        """
        if self.measurement.length_unit and isinstance(self.raw, Decimal):
            return format_length_for_language(self.raw, self.measurement.length_unit, locale)
        token = self.raw if isinstance(self.raw, str) else format_raw(self.raw)
        if self.measurement.display_prefix:
            return f"{self.measurement.display_prefix}{token}"
        if self.measurement.display_suffix:
            return f"{token}{self.measurement.display_suffix}"
        return token

    def convert(
        self,
        target: Measurement | Locale | str,
        *,
        age_group: AgeGroup | str | None = None,
        gender: Gender | str | None = None,
        brand_scale: ConversionScale | None = None,
    ) -> MeasurementValue:
        """Convert to another measurement on the same kind.

        ``target`` may be a concrete ``Measurement``, a chart locale
        (``Locale.EU`` / ``"eu"``), or a length unit (``"cm"`` / ``"in"``).
        Dress, shoe, and cup-size charts are selected by ``age_group`` and ``gender``.
        """
        # Imported here to avoid a load-time cycle with fashion_size.conversion.
        from fashion_size.conversion import convert as convert_measurement_value

        return convert_measurement_value(
            self,
            target,
            age_group=age_group,
            gender=gender,
            brand_scale=brand_scale,
        )

    def convert_to_locale(
        self,
        product_type_group_id: int | None,
        target_locale: Locale | str,
        *,
        brand: Any,
        age_group: AgeGroup | str,
        gender: Gender | str,
    ) -> MeasurementValue:
        """Convert this value into ``target_locale`` for a product family.

        Resolves the target measurement from this value's kind and the locale
        (a UK dress size and ``"eu"`` become an EU dress size; a UK cup size and
        ``Locale.US`` become a US cup size). Uses this brand's chart for
        ``product_type_group_id`` when one is saved, otherwise the brand chart
        with no group, otherwise the hardcoded default. Pass ``None`` when the
        product has no product type group.

        ``brand``, ``age_group``, and ``gender`` select the chart. Length kinds
        have no locale chart; use ``convert`` with ``"cm"`` or ``"in"``.

        The host application registers how ``brand`` is resolved
        (``register_brand_converter``). This package does not import the host's
        brand model.
        """
        from fashion_size.brand_lookup import convert_with_brand

        return convert_with_brand(
            self,
            target_locale,
            age_group=age_group,
            gender=gender,
            brand=brand,
            product_type_group=product_type_group_id,
        )

    def __str__(self) -> str:
        return self.localised_display()
