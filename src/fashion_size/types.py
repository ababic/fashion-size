"""Size types, size units, and sizes.

A ``Size`` is an amount in a ``SizeUnit``, such as ``UK_DRESS_SIZE`` or
``CM_CHEST_SIZE``. The unit knows its ``SizeType`` and its locale
(``universal`` for centimetres and inches). Default conversion charts live in
``fashion_size.scales``. Brand charts are JSON files named by id — see
``fashion_size.charts``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum
from typing import Literal

from fashion_size.brands import BrandName
from fashion_size.charts import BrandConversionChart
from fashion_size.demographics import (
    DEMOGRAPHIC_LABELS,
    AgeGroup,
    Demographic,
    Gender,
    age_group_label,
    gender_label,
)
from fashion_size.product_types import ProductType
from fashion_size.size_types import SizeTypeSlug


class SizeFamily(StrEnum):
    """Groups of size types that convert the same way."""

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
        return self not in {SizeFamily.LENGTH, SizeFamily.BAND_SIZE}

    @property
    def french_matches_eu(self) -> bool:
        """French dress, shoe, cup, and chest-size labels are the EU size.

        Waist size is not: French swim and trouser charts use a different number.
        Band size is not either: a French band is the EU centimetre label plus 15.
        """
        return self in {
            SizeFamily.DRESS_SIZE,
            SizeFamily.SHOE_SIZE,
            SizeFamily.CUP_SIZE,
            SizeFamily.CHEST_SIZE,
        }


class Locale(StrEnum):
    """Regional size system, or ``universal`` for centimetres / inches."""

    UNIVERSAL = "universal"
    UK = "uk"
    EU = "eu"
    US = "us"
    AU = "au"
    FR = "fr"


# Chart columns. French is not a column: dress, shoe, and cup sizes use the EU size.
# French band size is the EU centimetre label plus this offset (EU 75 = FR 90).
CHART_LOCALES: tuple[Locale, ...] = (Locale.UK, Locale.EU, Locale.US, Locale.AU)
FRENCH_BAND_OFFSET = Decimal(15)


class IncompatibleSizeError(ValueError):
    """Source and target size units do not share a size type."""


class UnknownSizeError(ValueError):
    """The raw value is not on the conversion chart for this size type and demographic."""


class MissingScaleError(ValueError):
    """No default (or brand) chart exists for this size type and demographic."""


class LengthOutOfRangeError(ValueError):
    """Length is outside the clothing / accessories / curtain range (5–150 inches)."""


def _finite_decimal(value: int | float | str | Decimal) -> Decimal:
    """Parse a size. ``inf`` and ``nan`` are not sizes."""
    raw = value if isinstance(value, Decimal) else Decimal(str(value))
    if not raw.is_finite():
        raise ValueError(f"Non-finite size {value!r}")
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

# Sports-bra and bralette alpha labels (not regional cup letters). Stored verbatim;
# locale conversion is identity. ``Small`` / ``Medium`` / ``Large`` avoid clashing
# with cup ``L`` and ``M``. Bare ``l`` / ``m`` still mean cup letters.
CUP_ALPHA_TOKENS: frozenset[str] = frozenset(
    {"XXS", "XS", "Small", "Medium", "Large", "XL", "XXL"}
)

_CUP_ALPHA_ALIASES: dict[str, str] = {
    "xxs": "XXS",
    "xs": "XS",
    "xsmall": "XS",
    "extrasmall": "XS",
    "s": "Small",
    "sm": "Small",
    "small": "Small",
    "medium": "Medium",
    "med": "Medium",
    "large": "Large",
    "lg": "Large",
    "xl": "XL",
    "xlarge": "XL",
    "xxl": "XXL",
    "2xl": "XXL",
}


def _cup_alpha_lookup_key(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("-", "")


def is_cup_alpha_token(value: str) -> bool:
    """Whether ``value`` is a canonical alpha cup label (after normalization)."""
    return value in CUP_ALPHA_TOKENS


def normalize_cup_token(value: object) -> str:
    """Canonical cup letter (``dd`` → ``DD``) or alpha label (``small`` → ``Small``).

    Alpha labels convert identically across UK / EU / US / AU. Single-letter ``l``
    and ``m`` are cup letters, not ``Large`` / ``Medium`` — use the full words or
    ``lg`` / ``med`` for alpha.
    """
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Unknown cup size {value!r}.")
    if text in CUP_ALPHA_TOKENS:
        return text
    alpha = _CUP_ALPHA_ALIASES.get(_cup_alpha_lookup_key(text))
    if alpha is not None:
        return alpha
    token = text.upper().replace(" ", "")
    if token in CUP_TOKENS:
        return token
    raise ValueError(f"Unknown cup size {value!r}.")


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
    language = (
        (locale or active_display_language() or "en-gb")
        .replace("_", "-")
        .strip()
        .lower()
    )
    return language or "en-gb"


def uses_inch_quote(locale: str | None = None) -> bool:
    """English locales typically mark inches with ``"``; others prefer `` in``."""
    language = resolve_display_language(locale)
    return language == "en" or language.startswith("en-")


def format_length_for_language(
    raw: Decimal | int | float | str, unit: str, locale: str | None = None
) -> str:
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


def resolve_age_gender(
    age_group: AgeGroup | str, gender: Gender | str
) -> tuple[str, str]:
    """Normalise an ``AgeGroup`` × ``Gender`` pair to ``(age_group, gender)`` values.

    This is the same pair used on catalogue items (``adult`` / ``child`` / ``baby``
    with ``male`` / ``female`` / ``unisex``). Unisex adults and children are valid
    pairs; whether a chart exists for them is decided by the scale lookup.
    """
    age = (
        age_group.value
        if isinstance(age_group, AgeGroup)
        else str(age_group or "").strip().lower()
    )
    sex = (
        gender.value
        if isinstance(gender, Gender)
        else str(gender or "").strip().lower()
    )
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
class SizeType:
    """Fine-grained size category (dress, adult shoe, chest, …).

    Adult, kids, and baby shoes are separate size types. UK 7 adult is not UK 7 kids.
    """

    slug: str
    family: SizeFamily
    label: str
    attribute_slugs: tuple[str, ...] = ()
    # SizeUnit slug stem when it must not also be an attribute-slug alias.
    # ``uk-waist-size`` is the regional label; ``waist-size`` stays the length size type.
    slug_stem: str = ""

    @property
    def supports_brand_overrides(self) -> bool:
        return self.family.supports_brand_overrides

    def __str__(self) -> str:
        return self.label


DRESS = SizeType(
    SizeTypeSlug.DRESS,
    SizeFamily.DRESS_SIZE,
    "Dress size",
    ("dress-size",),
)
ADULT_SHOE = SizeType(
    SizeTypeSlug.ADULT_SHOE,
    SizeFamily.SHOE_SIZE,
    "Adult shoe size",
    ("adult-shoe-size", "shoe-size", "european-shoe-size"),
)
KIDS_SHOE = SizeType(
    SizeTypeSlug.KIDS_SHOE,
    SizeFamily.SHOE_SIZE,
    "Kids shoe size",
    ("kids-shoe-size",),
)
BABY_SHOE = SizeType(
    SizeTypeSlug.BABY_SHOE,
    SizeFamily.SHOE_SIZE,
    "Baby shoe size",
    ("baby-shoe-size",),
)
CUP_SIZE = SizeType(
    SizeTypeSlug.CUP_SIZE,
    SizeFamily.CUP_SIZE,
    "Cup size",
    ("cup-size", "bra-cup", "bra-cup-size"),
)
# Underbust band. Distinct from chest size (a jacket label) and from cup size.
BAND_SIZE = SizeType(
    SizeTypeSlug.BAND_SIZE,
    SizeFamily.BAND_SIZE,
    "Band size",
    ("bra-band-size",),
    slug_stem="band-size",
)
# Regional garment labels. UK/US/AU are the inch number; EU/IT is a different number.
# Distinct from the length size types, which only convert centimetres and inches.
WAIST_SIZE = SizeType(
    SizeTypeSlug.WAIST_SIZE,
    SizeFamily.WAIST_SIZE,
    "Waist size",
    slug_stem="waist-size",
)
CHEST_SIZE = SizeType(
    SizeTypeSlug.CHEST_SIZE,
    SizeFamily.CHEST_SIZE,
    "Chest size",
    slug_stem="chest-size",
)
CHEST = SizeType(SizeTypeSlug.CHEST, SizeFamily.LENGTH, "Chest", ("chest-size",))
WAIST = SizeType(SizeTypeSlug.WAIST, SizeFamily.LENGTH, "Waist", ("waist-size",))
INSIDE_LEG = SizeType(
    SizeTypeSlug.INSIDE_LEG,
    SizeFamily.LENGTH,
    "Inside leg",
    ("inside-leg", "leg-length"),
)
COLLAR = SizeType(SizeTypeSlug.COLLAR, SizeFamily.LENGTH, "Collar", ("collar-size",))

SIZE_TYPES: tuple[SizeType, ...] = (
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
SIZE_TYPE_BY_SLUG: dict[str, SizeType] = {
    size_type.slug: size_type for size_type in SIZE_TYPES
}
BRAND_CHART_SIZE_TYPE_SLUGS: frozenset[str] = frozenset(
    size_type.slug for size_type in SIZE_TYPES if size_type.supports_brand_overrides
)
ATTRIBUTE_SIZE_TYPES: dict[str, SizeType] = {
    slug: size_type for size_type in SIZE_TYPES for slug in size_type.attribute_slugs
}


@dataclass(frozen=True, slots=True)
class SizeUnit:
    """A concrete size expression bound to one size type.

    Examples: ``UK_DRESS_SIZE``, ``EU_ADULT_SHOE_SIZE``, ``CM_CHEST_SIZE``.
    Locale is ``universal`` for centimetres and inches; otherwise UK / EU / US / AU.
    """

    slug: str
    size_type: SizeType
    locale: Locale
    label: str
    display_suffix: str = ""
    display_prefix: str = ""
    length_unit: str | None = None

    @property
    def supports_brand_overrides(self) -> bool:
        return self.size_type.supports_brand_overrides

    def can_convert_to(self, other: SizeUnit) -> bool:
        return self.size_type.slug == other.size_type.slug

    def __str__(self) -> str:
        return self.label


def _locale_size_unit(size_type: SizeType, locale: Locale) -> SizeUnit:
    attribute = size_type.slug_stem or size_type.attribute_slugs[0]
    # Cup sizes display as the letter alone (``DD``). Dress and shoe sizes keep a region prefix.
    prefix = (
        "" if size_type.family == SizeFamily.CUP_SIZE else f"{locale.value.upper()} "
    )
    return SizeUnit(
        slug=f"{locale.value}-{attribute}",
        size_type=size_type,
        locale=locale,
        label=f"{locale.value.upper()} {size_type.label}",
        display_prefix=prefix,
    )


def _length_size_unit(
    size_type: SizeType, *, unit: str, display_suffix: str, label_unit: str
) -> SizeUnit:
    attribute = size_type.attribute_slugs[0]
    return SizeUnit(
        slug=f"{unit}-{attribute}",
        size_type=size_type,
        locale=Locale.UNIVERSAL,
        label=f"{size_type.label} ({label_unit})",
        display_suffix=display_suffix,
        length_unit=unit,
    )


UK_DRESS_SIZE = _locale_size_unit(DRESS, Locale.UK)
EU_DRESS_SIZE = _locale_size_unit(DRESS, Locale.EU)
US_DRESS_SIZE = _locale_size_unit(DRESS, Locale.US)
AU_DRESS_SIZE = _locale_size_unit(DRESS, Locale.AU)

UK_ADULT_SHOE_SIZE = _locale_size_unit(ADULT_SHOE, Locale.UK)
EU_ADULT_SHOE_SIZE = _locale_size_unit(ADULT_SHOE, Locale.EU)
US_ADULT_SHOE_SIZE = _locale_size_unit(ADULT_SHOE, Locale.US)
AU_ADULT_SHOE_SIZE = _locale_size_unit(ADULT_SHOE, Locale.AU)

UK_KIDS_SHOE_SIZE = _locale_size_unit(KIDS_SHOE, Locale.UK)
EU_KIDS_SHOE_SIZE = _locale_size_unit(KIDS_SHOE, Locale.EU)
US_KIDS_SHOE_SIZE = _locale_size_unit(KIDS_SHOE, Locale.US)
AU_KIDS_SHOE_SIZE = _locale_size_unit(KIDS_SHOE, Locale.AU)

UK_BABY_SHOE_SIZE = _locale_size_unit(BABY_SHOE, Locale.UK)
EU_BABY_SHOE_SIZE = _locale_size_unit(BABY_SHOE, Locale.EU)
US_BABY_SHOE_SIZE = _locale_size_unit(BABY_SHOE, Locale.US)
AU_BABY_SHOE_SIZE = _locale_size_unit(BABY_SHOE, Locale.AU)

UK_CUP_SIZE = _locale_size_unit(CUP_SIZE, Locale.UK)
EU_CUP_SIZE = _locale_size_unit(CUP_SIZE, Locale.EU)
US_CUP_SIZE = _locale_size_unit(CUP_SIZE, Locale.US)
AU_CUP_SIZE = _locale_size_unit(CUP_SIZE, Locale.AU)

UK_BAND_SIZE = _locale_size_unit(BAND_SIZE, Locale.UK)
EU_BAND_SIZE = _locale_size_unit(BAND_SIZE, Locale.EU)
US_BAND_SIZE = _locale_size_unit(BAND_SIZE, Locale.US)
AU_BAND_SIZE = _locale_size_unit(BAND_SIZE, Locale.AU)
# French band is its own label (EU centimetres + 15), not an alias of EU.
FR_BAND_SIZE = _locale_size_unit(BAND_SIZE, Locale.FR)

# French dress, shoe, and cup sizes are the EU size.
FR_DRESS_SIZE = EU_DRESS_SIZE
FR_ADULT_SHOE_SIZE = EU_ADULT_SHOE_SIZE
FR_KIDS_SHOE_SIZE = EU_KIDS_SHOE_SIZE
FR_BABY_SHOE_SIZE = EU_BABY_SHOE_SIZE
FR_CUP_SIZE = EU_CUP_SIZE

UK_WAIST_SIZE = _locale_size_unit(WAIST_SIZE, Locale.UK)
EU_WAIST_SIZE = _locale_size_unit(WAIST_SIZE, Locale.EU)
US_WAIST_SIZE = _locale_size_unit(WAIST_SIZE, Locale.US)
AU_WAIST_SIZE = _locale_size_unit(WAIST_SIZE, Locale.AU)

UK_CHEST_SIZE = _locale_size_unit(CHEST_SIZE, Locale.UK)
EU_CHEST_SIZE = _locale_size_unit(CHEST_SIZE, Locale.EU)
US_CHEST_SIZE = _locale_size_unit(CHEST_SIZE, Locale.US)
AU_CHEST_SIZE = _locale_size_unit(CHEST_SIZE, Locale.AU)
# French chest-size labels match EU. French waist size does not.
FR_CHEST_SIZE = EU_CHEST_SIZE

INCH_CHEST_SIZE = _length_size_unit(
    CHEST, unit="in", display_suffix='"', label_unit="inches"
)
CM_CHEST_SIZE = _length_size_unit(
    CHEST, unit="cm", display_suffix="cm", label_unit="centimetres"
)
INCH_WAIST_SIZE = _length_size_unit(
    WAIST, unit="in", display_suffix='"', label_unit="inches"
)
CM_WAIST_SIZE = _length_size_unit(
    WAIST, unit="cm", display_suffix="cm", label_unit="centimetres"
)
INCH_INSIDE_LEG = _length_size_unit(
    INSIDE_LEG, unit="in", display_suffix='"', label_unit="inches"
)
CM_INSIDE_LEG = _length_size_unit(
    INSIDE_LEG, unit="cm", display_suffix="cm", label_unit="centimetres"
)
INCH_COLLAR_SIZE = _length_size_unit(
    COLLAR, unit="in", display_suffix='"', label_unit="inches"
)
CM_COLLAR_SIZE = _length_size_unit(
    COLLAR, unit="cm", display_suffix="cm", label_unit="centimetres"
)

SIZE_UNITS: tuple[SizeUnit, ...] = (
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
SIZE_UNIT_BY_SLUG: dict[str, SizeUnit] = {
    size_unit.slug: size_unit for size_unit in SIZE_UNITS
}
for _size_unit in SIZE_UNITS:
    if _size_unit.locale is Locale.EU and _size_unit.size_type.family.french_matches_eu:
        SIZE_UNIT_BY_SLUG["fr-" + _size_unit.slug.removeprefix("eu-")] = _size_unit


def resolve_locale(value: Locale | str) -> Locale:
    """Accept a ``Locale`` enum or a slug such as ``uk`` / ``eu``."""
    if isinstance(value, Locale):
        return value
    normalized = str(value or "").strip().lower().replace("_", "-")
    try:
        return Locale(normalized)
    except ValueError as exc:
        raise ValueError(f"Unknown locale {value!r}") from exc


def size_unit_for_locale(size_type: SizeType, locale: Locale | str) -> SizeUnit:
    """Return the size unit for a chart locale (``uk``, ``eu``, …).

    Length size types use ``universal`` for both centimetres and inches, so pass a
    concrete ``SizeUnit`` (or use ``size_unit_for_length_unit``) instead.
    """
    if size_type.family == SizeFamily.LENGTH:
        raise IncompatibleSizeError(
            f"Cannot convert {size_type.label} to a chart locale — only centimetres and inches apply."
        )
    resolved = resolve_locale(locale)
    if resolved is Locale.FR and size_type.family.french_matches_eu:
        resolved = Locale.EU
    if resolved is Locale.UNIVERSAL:
        raise IncompatibleSizeError(
            f"Cannot convert {size_type.label} to centimetres or inches — only UK/EU/US/AU locales apply."
        )
    matches = tuple(
        m
        for m in SIZE_UNITS
        if m.size_type.slug == size_type.slug and m.locale is resolved
    )
    if not matches:
        raise ValueError(
            f"No {size_type.label} size unit for locale {resolved.value!r}."
        )
    if len(matches) > 1:
        raise ValueError(
            f"{size_type.label} has multiple size units for locale {resolved.value!r}; "
            "pass a concrete SizeUnit (e.g. centimetres or inches)."
        )
    return matches[0]


def size_unit_for_length_unit(size_type: SizeType, unit: str) -> SizeUnit:
    """Return the centimetre or inch size unit for this size type."""
    if size_type.family != SizeFamily.LENGTH:
        raise IncompatibleSizeError(
            f"Cannot convert {size_type.label} to centimetres or inches — only UK/EU/US/AU locales apply."
        )
    normalized = str(unit or "").strip().lower()
    if normalized in {"in", "inch", "inches", '"'}:
        normalized = "in"
    elif normalized in {"cm", "centimetre", "centimetres", "centimeter", "centimeters"}:
        normalized = "cm"
    else:
        raise ValueError(f"Unknown length unit {unit!r}.")
    for size_unit in SIZE_UNITS:
        if (
            size_unit.size_type.slug == size_type.slug
            and size_unit.length_unit == normalized
        ):
            return size_unit
    raise ValueError(f"No {size_type.label} size unit for unit {normalized!r}.")


def resolve_target_size_unit(
    size_type: SizeType, target: SizeUnit | Locale | str
) -> SizeUnit:
    """Resolve a convert target: a ``SizeUnit``, chart locale, or length unit.

    Length size types only accept ``cm`` / ``in`` (or a concrete length ``SizeUnit``).
    Chart size types accept UK / EU / US / AU / FR. French dress, shoe, cup, and chest
    sizes are the EU size. French waist size is not. French band size is the EU
    centimetre label plus 15. A target on another size type raises
    ``IncompatibleSizeError``.
    """
    if isinstance(target, SizeUnit):
        if target.size_type.slug != size_type.slug:
            raise IncompatibleSizeError(
                f"Cannot convert {size_type.label} to {target.label} — size units must share a size type."
            )
        return target
    if isinstance(target, Locale):
        return size_unit_for_locale(size_type, target)
    normalized = str(target or "").strip().lower()
    if normalized in {"uk", "eu", "us", "au", "fr", "universal"}:
        return size_unit_for_locale(size_type, normalized)
    if normalized in {
        "cm",
        "centimetre",
        "centimetres",
        "centimeter",
        "centimeters",
        "in",
        "inch",
        "inches",
        '"',
    }:
        return size_unit_for_length_unit(size_type, normalized)
    return size_unit_for_locale(size_type, target)


def size_type_for_attribute(attribute_slug: str) -> SizeType | None:
    """Return the size type bound to a catalog attribute slug, if any."""
    key = (attribute_slug or "").strip()
    if key in SIZE_UNIT_BY_SLUG:
        return SIZE_UNIT_BY_SLUG[key].size_type
    return ATTRIBUTE_SIZE_TYPES.get(key)


def parse_size_unit_slug(slug: str) -> SizeUnit:
    """Return the size unit for a slug such as ``uk-dress-size``."""
    key = (slug or "").strip().lower()
    try:
        return SIZE_UNIT_BY_SLUG[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown size unit {slug!r}. Expected a slug such as 'uk-dress-size' or 'cm-chest-size'."
        ) from exc


def size_unit_choices() -> list[tuple[str, str]]:
    """``(slug, label)`` pairs for every size unit — usable as model field ``choices``."""
    return [(size_unit.slug, size_unit.label) for size_unit in SIZE_UNITS]


def size_unit_choices_for_type(size_type_slug: str) -> list[tuple[str, str]]:
    """``(slug, label)`` pairs for the size units of one size type."""
    key = (size_type_slug or "").strip().lower()
    if not key:
        return []
    return [
        (size_unit.slug, size_unit.label)
        for size_unit in SIZE_UNITS
        if size_unit.size_type.slug == key
    ]


def size_from_attribute_option(
    slug: str,
    value: str,
    *,
    raw_value_prefix: str = "",
    raw_value_suffix: str = "",
) -> Size | None:
    """Build a ``Size`` from an attribute option's size-unit slug and text.

    ``slug`` is the size-unit slug stored on the option (for example
    ``uk-dress-size``). ``value`` is the stored option text (``10``, ``UK 10``,
    ``32"``). Affixes are stripped using ``raw_value_prefix`` and
    ``raw_value_suffix`` when set, otherwise the size unit's display prefix and
    suffix. Returns ``None`` when the slug is unknown or the value is not a size.
    """
    size_unit = SIZE_UNIT_BY_SLUG.get((slug or "").strip().lower())
    if size_unit is None:
        return None
    text = (value or "").strip()
    prefix = raw_value_prefix if raw_value_prefix.strip() else size_unit.display_prefix
    suffix = raw_value_suffix if raw_value_suffix.strip() else size_unit.display_suffix
    if prefix and text.upper().startswith(prefix.upper()):
        text = text[len(prefix) :].strip()
    if suffix and text.endswith(suffix):
        text = text[: -len(suffix)].strip()
    if not text:
        return None
    try:
        if size_unit.size_type.family == SizeFamily.CUP_SIZE:
            return Size(raw=normalize_cup_token(text), size_unit=size_unit)
        if size_unit.size_type.family == SizeFamily.LENGTH:
            return Size(raw=normalize_length_raw(text), size_unit=size_unit)
        return Size(raw=normalize_raw(text), size_unit=size_unit)
    except (InvalidOperation, ValueError, TypeError):
        return None


def size_type_from_slug(slug: str) -> SizeType:
    try:
        return SIZE_TYPE_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"Unknown size type {slug!r}") from exc


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
    def from_tokens(
        cls, uk: object, eu: object, us: object, au: object
    ) -> LetterSizeRow:
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
    """A complete value set for one size type and one age-group × gender pair."""

    size_type: SizeType
    age_group: str
    gender: str
    rows: tuple[LocaleSizeRow, ...] | tuple[LetterSizeRow, ...]

    def _chart_locale_and_needle(
        self,
        raw: int | float | str | Decimal,
        size_unit: SizeUnit,
    ) -> tuple[Locale, Decimal | str]:
        """Column and value to look up. French band labels sit 15 above the EU column."""
        if self.size_type.family == SizeFamily.CUP_SIZE:
            return size_unit.locale, normalize_cup_token(raw)
        number = normalize_raw(raw)
        if (
            self.size_type.family is SizeFamily.BAND_SIZE
            and size_unit.locale is Locale.FR
        ):
            return Locale.EU, number - FRENCH_BAND_OFFSET
        return size_unit.locale, number

    def _value_for_size_unit(
        self, row: LocaleSizeRow | LetterSizeRow, size_unit: SizeUnit
    ) -> Decimal | str:
        if (
            self.size_type.family is SizeFamily.BAND_SIZE
            and size_unit.locale is Locale.FR
        ):
            return normalize_raw(row.value_for(Locale.EU)) + FRENCH_BAND_OFFSET
        return row.value_for(size_unit.locale)

    def raw_values(self, size_unit: SizeUnit) -> tuple[Decimal, ...] | tuple[str, ...]:
        """All stored raw values for one locale — the attribute's value set in that locale."""
        return tuple(self._value_for_size_unit(row, size_unit) for row in self.rows)

    def row_for(
        self, raw: int | float | str | Decimal, size_unit: SizeUnit
    ) -> LocaleSizeRow | LetterSizeRow:
        locale, needle = self._chart_locale_and_needle(raw, size_unit)
        for row in self.rows:
            if row.value_for(locale) == needle:
                return row
        if self.size_type.family == SizeFamily.CUP_SIZE:
            shown = needle if isinstance(needle, str) else format_raw(needle)
        else:
            shown = format_raw(normalize_raw(raw))
        raise UnknownSizeError(
            f"{self.size_type.label} {shown} ({size_unit.label}) is not on the "
            f"{format_age_gender(self.age_group, self.gender)} conversion chart."
        )

    def convert_raw(
        self,
        raw: int | float | str | Decimal,
        source: SizeUnit,
        target: SizeUnit,
    ) -> Decimal | str:
        if self.size_type.family == SizeFamily.CUP_SIZE:
            token = normalize_cup_token(raw)
            if is_cup_alpha_token(token):
                return token
        if source == target:
            if self.size_type.family == SizeFamily.CUP_SIZE:
                return normalize_cup_token(raw)
            return normalize_raw(raw)
        return self._value_for_size_unit(self.row_for(raw, source), target)


@dataclass(frozen=True, slots=True)
class Size:
    """An amount stored in a ``SizeUnit``.

    Numeric size types store a ``Decimal``. Cup size stores the letter for that
    locale (``DD``, ``E``, ``DDD``).
    """

    raw: Decimal | str
    size_unit: SizeUnit

    def __post_init__(self) -> None:
        if self.size_unit.size_type.family == SizeFamily.CUP_SIZE:
            object.__setattr__(self, "raw", normalize_cup_token(self.raw))
        elif self.size_unit.size_type.family == SizeFamily.LENGTH:
            object.__setattr__(self, "raw", normalize_length_raw(self.raw))
        else:
            object.__setattr__(self, "raw", normalize_raw(self.raw))

    @property
    def size_type(self) -> SizeType:
        return self.size_unit.size_type

    @classmethod
    def from_raw(cls, raw: int | float | str | Decimal, size_unit: SizeUnit) -> Size:
        return cls(raw=raw, size_unit=size_unit)

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
        if self.size_unit.length_unit and isinstance(self.raw, Decimal):
            return format_length_for_language(
                self.raw, self.size_unit.length_unit, locale
            )
        token = self.raw if isinstance(self.raw, str) else format_raw(self.raw)
        if self.size_unit.display_prefix:
            return f"{self.size_unit.display_prefix}{token}"
        if self.size_unit.display_suffix:
            return f"{token}{self.size_unit.display_suffix}"
        return token

    def convert(
        self,
        unit: SizeUnit | Literal["cm", "in"],
        *,
        demographic: Demographic,
        brand_name: BrandName | str | None = None,
        product_type: ProductType | str | None = None,
        strict_brand_name: bool = False,
    ) -> ConvertedSize:
        """Convert to ``unit`` on this size type.

        ``unit`` is a ``SizeUnit`` for this size type, or ``"cm"`` / ``"in"`` for a
        length. Chart locales use ``convert_to_locale``. The result records how the
        size was produced and cannot be converted again.
        """
        from fashion_size.conversion import convert as convert_size

        return convert_size(
            self,
            unit,
            demographic=demographic,
            brand_name=brand_name,
            product_type=product_type,
            strict_brand_name=strict_brand_name,
        )

    def convert_to_locale(
        self,
        locale: Locale | str,
        *,
        demographic: Demographic,
        brand_name: BrandName | str | None = None,
        product_type: ProductType | str | None = None,
        strict_brand_name: bool = False,
    ) -> ConvertedSize:
        """Convert to the ``SizeUnit`` for ``locale`` on this size type.

        ``locale`` is a ``Locale`` or a slug such as ``"eu"``. This resolves the
        locale and calls ``convert``.
        """
        from fashion_size.conversion import convert_to_locale as convert_locale

        return convert_locale(
            self,
            locale,
            demographic=demographic,
            brand_name=brand_name,
            product_type=product_type,
            strict_brand_name=strict_brand_name,
        )

    def __str__(self) -> str:
        return self.localised_display()


class ConversionSourceKind(StrEnum):
    """How a ``ConvertedSize`` was produced."""

    IDENTITY = "identity"
    DEFAULT = "default"
    BRAND = "brand"
    LENGTH_FORMULA = "length_formula"


class DefaultChartReason(StrEnum):
    """Why a default chart was used instead of a brand chart."""

    NO_BRAND = "no_brand"
    UNKNOWN_BRAND = "unknown_brand"
    BRAND_USES_DEFAULT = "brand_uses_default"
    NO_MATCHING_CHART = "no_matching_chart"
    SIZE_TYPE_USES_DEFAULT = "size_type_uses_default"


@dataclass(frozen=True, slots=True)
class ConversionSource:
    """Chart or formula used for one conversion."""

    kind: ConversionSourceKind
    brand_chart: BrandConversionChart | None = None
    default_scale: ConversionScale | None = None
    default_reason: DefaultChartReason | None = None
    brand_name: BrandName | str | None = None

    def __post_init__(self) -> None:
        if self.kind is ConversionSourceKind.IDENTITY and (
            self.brand_chart is not None
            or self.default_scale is not None
            or self.default_reason is not None
            or self.brand_name is not None
        ):
            raise ValueError("An identity conversion has no chart.")
        if self.kind is ConversionSourceKind.BRAND and (
            self.brand_chart is None
            or self.default_scale is not None
            or self.default_reason is not None
        ):
            raise ValueError("A brand conversion needs a brand chart.")
        if self.kind is ConversionSourceKind.DEFAULT and (
            self.default_scale is None
            or self.brand_chart is not None
            or self.default_reason is None
        ):
            raise ValueError("A default conversion needs a default scale and reason.")
        if self.kind is ConversionSourceKind.LENGTH_FORMULA and (
            self.brand_chart is not None
            or self.default_scale is not None
            or self.default_reason is not None
            or self.brand_name is not None
        ):
            raise ValueError("A length conversion has no chart.")

    @classmethod
    def identity(cls) -> ConversionSource:
        return cls(ConversionSourceKind.IDENTITY)

    @classmethod
    def default(
        cls,
        scale: ConversionScale,
        *,
        reason: DefaultChartReason,
        brand_name: BrandName | str | None = None,
    ) -> ConversionSource:
        return cls(
            ConversionSourceKind.DEFAULT,
            default_scale=scale,
            default_reason=reason,
            brand_name=brand_name,
        )

    @classmethod
    def brand(cls, chart: BrandConversionChart) -> ConversionSource:
        return cls(
            ConversionSourceKind.BRAND,
            brand_chart=chart,
            brand_name=chart.brand_name,
        )

    @classmethod
    def length_formula(cls) -> ConversionSource:
        return cls(ConversionSourceKind.LENGTH_FORMULA)


@dataclass(frozen=True, slots=True)
class ConvertedSize:
    """A size produced by one conversion.

    ``source`` records how ``size`` was produced. This type has no ``convert``
    method.
    """

    size: Size
    source: ConversionSource

    @property
    def raw(self) -> Decimal | str:
        return self.size.raw

    @property
    def size_unit(self) -> SizeUnit:
        return self.size.size_unit

    @property
    def size_type(self) -> SizeType:
        return self.size.size_type

    def display(self) -> str:
        """Format with ``Size.display``."""
        return self.size.display()

    def localised_display(self, locale: str | None = None) -> str:
        """Format with ``Size.localised_display``."""
        return self.size.localised_display(locale)

    def __str__(self) -> str:
        return str(self.size)
