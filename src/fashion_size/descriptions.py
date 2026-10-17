"""Recognise feed size strings and render a series of sizes back to text.

Importing this module compiles the format patterns. ``fashion_size`` itself
does not import it, so the patterns stay out of memory until these APIs run.

Chart sizes (dress, shoe, waist size, chest size, band, cup) are returned in
the region they were written in. Length measurements can move between
centimetres and inches. Label sizes (trouser length, top length, shoe width,
proportion, age) can be worded for a preferred region. Nothing here consults
a conversion chart.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from fashion_size.demographics import AgeGroup, Demographic, Gender
from fashion_size.product_types import ProductType
from fashion_size.types import (
    AGE_MONTHS_SIZE,
    AGE_YEARS_SIZE,
    AU_ADULT_SHOE_SIZE,
    AU_CHEST_SIZE,
    AU_DRESS_SIZE,
    AU_WAIST_SIZE,
    CM_COLLAR_SIZE,
    CM_WAIST_SIZE,
    CUP_TOKENS,
    EU_ADULT_SHOE_SIZE,
    EU_CHEST_SIZE,
    EU_DRESS_SIZE,
    EU_WAIST_SIZE,
    INCH_COLLAR_SIZE,
    INCH_SLEEVE_SIZE,
    INCH_TROUSERS_INSEAM,
    INCH_WAIST_SIZE,
    PROPORTION,
    PROPORTION_SIZE,
    SHOE_WIDTH,
    SHOE_WIDTH_SIZE,
    SIZE_UNITS,
    TOP_LENGTH_SIZE,
    TROUSER_LENGTH,
    TROUSER_LENGTH_SIZE,
    UK_ADULT_SHOE_SIZE,
    UK_BAND_SIZE,
    UK_CHEST_SIZE,
    UK_CUP_SIZE,
    UK_DRESS_SIZE,
    UK_WAIST_SIZE,
    US_ADULT_SHOE_SIZE,
    US_CHEST_SIZE,
    US_DRESS_SIZE,
    US_WAIST_SIZE,
    Locale,
    Size,
    SizeFamily,
    SizeUnit,
    format_raw,
    label_display,
    length_value_in_range,
    normalize_cup_token,
    normalize_raw,
    size_unit_for_length_unit,
)

_REGION_PREFIX = r"(?:UK|EU|EUR|US|AU|FR)"
_NUM = r"\d{1,2}(?:\.\d)?"

_BOTTOMS = frozenset(
    {
        ProductType.JEANS,
        ProductType.TROUSERS,
        ProductType.SHORTS,
        ProductType.CASUAL_BOTTOMS,
        ProductType.SUITS,
    }
)
_TOPS = frozenset(
    {
        ProductType.SHIRTS,
        ProductType.DRESS_SHIRTS,
        ProductType.CASUAL_TOPS,
        ProductType.KNITWEAR,
        ProductType.OUTERWEAR,
        ProductType.ACTIVEWEAR_TOPS,
    }
)
_FOOTWEAR = frozenset({ProductType.SHOES, ProductType.BOOTS, ProductType.TRAINERS})
_DRESS_LIKE = frozenset(
    {
        ProductType.DRESSES,
        ProductType.SKIRTS,
        ProductType.NIGHTWEAR,
        ProductType.SWIMWEAR,
    }
)

# UK retail width letters used on Clarks and similar feeds: D/E narrow, F standard, G wide, H extra wide.
_SHOE_WIDTH_LETTER = {
    "D": "narrow",
    "E": "narrow",
    "F": "standard",
    "G": "wide",
    "H": "extra-wide",
}

_REGION_WORDS: dict[str, dict[Locale, str]] = {
    "extra-short": {
        Locale.UK: "Extra short",
        Locale.US: "Extra short",
        Locale.EU: "Extra short",
        Locale.FR: "Très court",
    },
    "short": {
        Locale.UK: "Short",
        Locale.US: "Short",
        Locale.EU: "Short",
        Locale.FR: "Court",
    },
    "regular": {
        Locale.UK: "Regular",
        Locale.US: "Regular",
        Locale.EU: "Regular",
        Locale.FR: "Normal",
    },
    "long": {
        Locale.UK: "Long",
        Locale.US: "Long",
        Locale.EU: "Long",
        Locale.FR: "Long",
    },
    "extra-long": {
        Locale.UK: "Extra long",
        Locale.US: "Extra long",
        Locale.EU: "Extra long",
        Locale.FR: "Très long",
    },
    "extra-tall": {
        Locale.UK: "Extra tall",
        Locale.US: "Extra tall",
        Locale.EU: "Extra tall",
        Locale.FR: "Très grand",
    },
    "tall": {
        Locale.UK: "Tall",
        Locale.US: "Tall",
        Locale.EU: "Tall",
        Locale.FR: "Grand",
    },
    "petite": {
        Locale.UK: "Petite",
        Locale.US: "Petite",
        Locale.EU: "Petite",
        Locale.FR: "Petite",
    },
    "narrow": {
        Locale.UK: "Narrow",
        Locale.US: "Narrow",
        Locale.EU: "Narrow",
        Locale.FR: "Étroit",
    },
    "standard": {
        Locale.UK: "Standard",
        Locale.US: "Medium",
        Locale.EU: "Standard",
        Locale.FR: "Standard",
    },
    "wide": {
        Locale.UK: "Wide",
        Locale.US: "Wide",
        Locale.EU: "Wide",
        Locale.FR: "Large",
    },
    "extra-wide": {
        Locale.UK: "Extra wide",
        Locale.US: "Extra wide",
        Locale.EU: "Extra wide",
        Locale.FR: "Très large",
    },
}

_TROUSER_CODE = {
    "extra-short": "XS",
    "short": "S",
    "regular": "R",
    "long": "L",
    "extra-long": "XL",
}


@dataclass(frozen=True, slots=True)
class DiscardedToken:
    """A piece of the input that was not used."""

    text: str
    reason: str


@dataclass(frozen=True, slots=True)
class DecodedSizeDescription:
    """Sizes read from one feed string."""

    sizes: tuple[Size, ...]
    format_id: str | None
    confidence: float
    discarded: tuple[DiscardedToken, ...]
    alternatives: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EncodedSizeDescription:
    """One readable size string built from size values."""

    text: str
    format_id: str | None
    confidence: float
    used: tuple[Size, ...]
    discarded: tuple[DiscardedToken, ...]


@dataclass(frozen=True, slots=True)
class _Hit:
    format_id: str
    sizes: tuple[Size, ...]
    score: float
    discarded: tuple[DiscardedToken, ...] = ()


def _locale_dress(locale: Locale) -> SizeUnit:
    return {
        Locale.UK: UK_DRESS_SIZE,
        Locale.EU: EU_DRESS_SIZE,
        Locale.US: US_DRESS_SIZE,
        Locale.AU: AU_DRESS_SIZE,
        Locale.FR: EU_DRESS_SIZE,
    }[locale]


def _locale_shoe(locale: Locale) -> SizeUnit:
    return {
        Locale.UK: UK_ADULT_SHOE_SIZE,
        Locale.EU: EU_ADULT_SHOE_SIZE,
        Locale.US: US_ADULT_SHOE_SIZE,
        Locale.AU: AU_ADULT_SHOE_SIZE,
        Locale.FR: EU_ADULT_SHOE_SIZE,
    }.get(locale, UK_ADULT_SHOE_SIZE)


def _number(text: str) -> Decimal:
    return normalize_raw(text)


def _in_span(value: Decimal, low: int, high: int) -> bool:
    return Decimal(low) <= value <= Decimal(high)


def _prefix_locale(token: str, fallback: Locale) -> Locale:
    key = token.upper()
    if key in {"EUR", "EU", "FR"}:
        return Locale.EU if key != "FR" else Locale.FR
    if key == "US":
        return Locale.US
    if key == "AU":
        return Locale.AU
    if key == "UK":
        return Locale.UK
    return fallback


def _require_locale(value: Locale, *, name: str) -> Locale:
    if not isinstance(value, Locale):
        raise TypeError(f"{name} must be a Locale, not {type(value).__name__}.")
    if value is Locale.UNIVERSAL:
        raise ValueError(f"{name} must be a regional size system.")
    return value


def _require_product_type(value: ProductType | None) -> ProductType | None:
    if value is None:
        return None
    if not isinstance(value, ProductType):
        raise TypeError(
            f"product_type must be a ProductType, not {type(value).__name__}."
        )
    return value


def decode_size_description(
    value: str,
    source_region: Locale,
    product_type: ProductType | None = None,
) -> DecodedSizeDescription:
    """Read one feed size string into size values.

    ``source_region`` supplies the region when the string has no prefix.
    ``product_type`` drops formats that do not belong to that range and raises
    confidence when several formats could fit. ``confidence`` is ``1`` when a
    single format matches, and lower when another format was also plausible.
    """
    region = _require_locale(source_region, name="source_region")
    product = _require_product_type(product_type)
    text = " ".join((value or "").strip().split())
    if _PURE_RANGE.fullmatch(text):
        return DecodedSizeDescription(
            (), None, 0.0, (DiscardedToken(text, "range"),), ()
        )
    if not text:
        return DecodedSizeDescription((), None, 0.0, (), ())
    hits = [
        hit for parser in _PARSERS if (hit := parser(text, region, product)) is not None
    ]
    if not hits:
        return DecodedSizeDescription(
            (),
            None,
            0.0,
            (DiscardedToken(text, "unrecognised"),),
            (),
        )
    hits.sort(key=lambda hit: hit.score, reverse=True)
    best = hits[0]
    alternatives = tuple(hit.format_id for hit in hits[1:4])
    confidence = best.score
    if alternatives and hits[1].score >= best.score - 0.15:
        confidence = min(confidence, 0.6)
    return DecodedSizeDescription(
        sizes=best.sizes,
        format_id=best.format_id,
        confidence=confidence,
        discarded=best.discarded,
        alternatives=alternatives,
    )


_LETTER_PREFIX = re.compile(r"\(\?<!\[A-Za-z\]\)[WL]")

# Context that looks like a size token but is a quantity, a year, a collection
# name, or a garment phrase. A recognition match that sits inside one of these
# is not a size.
_EXCEPTION_PATTERNS = (
    re.compile(r"\b\d+\s*-?\s*packs?\b", re.IGNORECASE),
    re.compile(r"\bpacks?\s+of\s+\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:19|20)\d{2}\b"),
    re.compile(r"\bpetite\s+(?:edit|collection|range|line)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:extra[\s-]+)?(?:long|short)\s+sleeves?\b",
        re.IGNORECASE,
    ),
)


def _overlaps_exception(text: str, start: int, end: int) -> bool:
    for pattern in _EXCEPTION_PATTERNS:
        for found in pattern.finditer(text):
            if found.start() < end and found.end() > start:
                return True
    return False


def _parse_from_units(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    """Find size values by each unit's own recognition patterns."""
    found: list[tuple[int, int, float, Size]] = []
    chart_region = Locale.EU if region is Locale.FR else region
    for unit in SIZE_UNITS:
        patterns = unit.recognition_patterns()
        for pattern in patterns:
            explicit = not unit.recognition_is_fallback(pattern)
            for match in pattern.finditer(text):
                value_at = (
                    match.start("value")
                    if "value" in match.groupdict()
                    else match.start()
                )
                if re.search(r"[-–]\s*$", text[:value_at]) or _RANGE_TAIL.match(
                    text[match.end() :]
                ):
                    continue
                if _overlaps_exception(text, match.start(), match.end()):
                    continue
                if unit.size_type.family is SizeFamily.CUP_SIZE and not _cup_span_ok(
                    text, match
                ):
                    continue
                built = _size_from_unit_match(
                    unit,
                    match.group("value"),
                    region=region,
                    chart_region=chart_region,
                    product=product,
                    explicit=explicit,
                )
                if built is None:
                    continue
                size, score = built
                if _LETTER_PREFIX.match(pattern.pattern):
                    score += 0.12
                    span = unit.size_type.length_range
                    if span is not None:
                        width = span.stop_inches - span.start_inches
                        score += 0.05 / float(width)
                found.append((match.start(), match.end(), score, size))
    chosen = _pick_nonoverlapping(found)
    if not chosen:
        return None
    sizes = tuple(item[3] for item in chosen)
    score = sum(item[2] for item in chosen) / len(chosen)
    covered = sum(item[1] - item[0] for item in chosen)
    if covered < len(text.replace(" ", "")) / 2 and len(sizes) == 1:
        score -= 0.15
    return _Hit("unit-patterns", sizes, max(score, 0.2))


def _cup_span_ok(text: str, match: re.Match[str]) -> bool:
    """A cup letter counts on its own, or immediately after a band number."""
    before = text[: match.start()].strip()
    after = text[match.end() :].strip()
    if not before and not after:
        return True
    return bool(re.search(r"\d$", before)) and not after


def _size_from_unit_match(
    unit: SizeUnit,
    raw: str,
    *,
    region: Locale,
    chart_region: Locale,
    product: ProductType | None,
    explicit: bool,
) -> tuple[Size, float] | None:
    if not explicit and unit.locale not in {Locale.UNIVERSAL, chart_region, region}:
        return None
    try:
        size = Size(raw, unit)
    except (ValueError, TypeError, InvalidOperation):
        return None
    if (
        unit.size_type.family is SizeFamily.LENGTH
        and isinstance(size.raw, Decimal)
        and not length_value_in_range(size.raw, unit)
    ):
        return None
    if not explicit and not _bare_value_fits(unit, product):
        return None
    score = 0.82 if explicit else 0.48
    affinity = _PRODUCT_AFFINITY.get(unit.size_type.slug)
    if product is not None and affinity is not None:
        score += 0.2 if product in affinity else -0.25
    if unit.locale is chart_region or unit.locale is region:
        score += 0.05
    if (
        unit.size_type.family is SizeFamily.CUP_SIZE
        and size.raw in {"S", "M", "L"}
        and product is not ProductType.BRAS
    ):
        score -= 0.45
    if unit.size_type.slug == "letter" and product is ProductType.BRAS:
        score -= 0.45
    return size, score


_PRODUCT_AFFINITY: dict[str, frozenset[ProductType]] = {
    "dress": _DRESS_LIKE,
    "adult-shoe": _FOOTWEAR,
    "kids-shoe": _FOOTWEAR,
    "baby-shoe": _FOOTWEAR,
    "cup-size": frozenset({ProductType.BRAS}),
    "band-size": frozenset({ProductType.BRAS}),
    "waist-size": _BOTTOMS,
    "chest-size": _TOPS,
    "chest": _TOPS,
    "waist": _BOTTOMS,
    "collar": frozenset({ProductType.SHIRTS, ProductType.DRESS_SHIRTS}),
    "inside-leg": _BOTTOMS,
    "shorts-inseam": frozenset({ProductType.SHORTS}),
    "trousers-inseam": _BOTTOMS,
    "trouser-length": _BOTTOMS,
    "top-length": _TOPS,
    "shoe-width": _FOOTWEAR,
    "proportion": _DRESS_LIKE | _TOPS,
    "letter": _DRESS_LIKE
    | _TOPS
    | _BOTTOMS
    | frozenset({ProductType.UNDERWEAR, ProductType.HOSIERY}),
}


def _bare_value_fits(unit: SizeUnit, product: ProductType | None) -> bool:
    affinity = _PRODUCT_AFFINITY.get(unit.size_type.slug)
    if product is None:
        return unit.size_type.slug in {"dress", "waist", "age"}
    if affinity is None:
        return True
    return product in affinity


def _pick_nonoverlapping(
    found: list[tuple[int, int, float, Size]],
) -> list[tuple[int, int, float, Size]]:
    ordered = sorted(found, key=lambda item: (item[2], item[1] - item[0]), reverse=True)
    chosen: list[tuple[int, int, float, Size]] = []
    for item in ordered:
        if any(not (item[1] <= kept[0] or item[0] >= kept[1]) for kept in chosen):
            continue
        if any(
            kept[3].size_type.slug == item[3].size_type.slug
            and kept[3].size_unit.locale == item[3].size_unit.locale
            for kept in chosen
        ):
            continue
        chosen.append(item)
    chosen.sort(key=lambda item: item[0])
    return chosen


_PURE_RANGE = re.compile(
    rf"^(?:{_REGION_PREFIX}\s*[-:]?\s*)?{_NUM}\s*[-–]\s*{_NUM}$",
    re.IGNORECASE,
)
_RANGE_TAIL = re.compile(rf"\s*[-–]\s*{_NUM}")
_REGION_VALUE = re.compile(
    rf"(?P<region>{_REGION_PREFIX})\s*[-:]?\s*(?P<value>{_NUM})",
    re.IGNORECASE,
)
_EU_WITH_UK = re.compile(
    rf"(?P<eu>{_NUM})\s*(?:/|\()\s*UK\s*-?\s*(?P<uk>{_NUM})\s*\)?",
    re.IGNORECASE,
)


def _regional_chart_unit(
    locale: Locale, number: Decimal, product: ProductType | None
) -> SizeUnit:
    resolved = Locale.EU if locale is Locale.FR else locale
    if product in _FOOTWEAR or (
        product is None and resolved is Locale.EU and _in_span(number, 35, 50)
    ):
        return _locale_shoe(resolved)
    if product in {ProductType.OUTERWEAR, ProductType.SUITS} and _in_span(
        number, 34, 60
    ):
        chest = {
            Locale.UK: UK_CHEST_SIZE,
            Locale.EU: EU_CHEST_SIZE,
            Locale.US: US_CHEST_SIZE,
            Locale.AU: AU_CHEST_SIZE,
        }
        return chest.get(resolved, UK_CHEST_SIZE)
    if product in _BOTTOMS and _in_span(number, 24, 50):
        waist = {
            Locale.UK: UK_WAIST_SIZE,
            Locale.EU: EU_WAIST_SIZE,
            Locale.US: US_WAIST_SIZE,
            Locale.AU: AU_WAIST_SIZE,
        }
        return waist.get(resolved, UK_WAIST_SIZE)
    return _locale_dress(resolved)


def _parse_regions(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    """Every labelled region in one cell, skipping a range such as ``UK 8-10``."""
    discarded: list[DiscardedToken] = []
    found: list[tuple[int, Size]] = []
    seen: set[tuple[str, Locale]] = set()

    def add(locale: Locale, raw: str, at: int) -> None:
        number = _number(raw)
        unit = _regional_chart_unit(locale, number, product)
        key = (unit.size_type.slug, unit.locale)
        if key in seen:
            return
        seen.add(key)
        found.append((at, Size(number, unit)))

    for match in _REGION_VALUE.finditer(text):
        if _RANGE_TAIL.match(text[match.end() :]):
            discarded.append(
                DiscardedToken(match.group(0) + text[match.end() :].split()[0], "range")
            )
            continue
        add(
            _prefix_locale(match.group("region"), region),
            match.group("value"),
            match.start(),
        )
    paired = _EU_WITH_UK.search(text)
    if paired and not _RANGE_TAIL.match(
        text[paired.start("eu") + len(paired.group("eu")) :]
    ):
        add(Locale.EU, paired.group("eu"), paired.start("eu"))
        add(Locale.UK, paired.group("uk"), paired.start("uk"))
    found.sort(key=lambda item: item[0])
    sizes = tuple(item[1] for item in found)
    if len(sizes) < 2 and not discarded:
        return None
    if not sizes:
        return _Hit("regions", (), 0.2, tuple(discarded))
    score = 0.98 if discarded else (0.96 if len(sizes) > 1 else 0.7)
    return _Hit("regions", sizes, score, tuple(discarded))


def _parse_numbered_fit(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    """``8R``, ``16T``, ``42R``, ``10 Full Length`` — one size plus a length word."""
    match = re.fullmatch(
        rf"({_NUM})\s*(R|T|X|S|L|full\s+length|petite|tall|extra\s+tall)",
        text,
        flags=re.IGNORECASE,
    )
    if match is None or _RANGE_TAIL.search(text):
        return None
    number = _number(match.group(1))
    word = match.group(2).casefold()
    proportion = {
        "r": "regular",
        "s": "short",
        "l": "long",
        "t": "tall",
        "x": "extra-tall",
        "petite": "petite",
        "tall": "tall",
        "extra tall": "extra-tall",
    }.get(word)
    if (
        word in {"r", "s", "l"}
        and _in_span(number, 24, 50)
        and product not in _DRESS_LIKE
        and product not in _TOPS
    ):
        return None
    if product in {ProductType.OUTERWEAR, ProductType.SUITS} and _in_span(
        number, 34, 60
    ):
        chart = _regional_chart_unit(region, number, product)
        label = Size(proportion or "regular", PROPORTION_SIZE)
        return _Hit("numbered-fit", (Size(number, chart), label), 0.9)
    if word == "full length":
        return _Hit(
            "numbered-fit",
            (
                Size(
                    number,
                    _locale_dress(region if region is not Locale.FR else Locale.EU),
                ),
                Size("long", TOP_LENGTH_SIZE),
            ),
            0.88,
        )
    if proportion is None:
        return None
    dress = Size(
        number, _locale_dress(region if region is not Locale.FR else Locale.EU)
    )
    return _Hit("numbered-fit", (dress, Size(proportion, PROPORTION_SIZE)), 0.88)


def _parse_collar_sleeve(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    """``15.5/34`` on a dress shirt is collar inches and sleeve inches."""
    if product not in {ProductType.DRESS_SHIRTS, ProductType.SHIRTS}:
        return None
    match = re.fullmatch(rf"({_NUM})\s*[/x]\s*(\d{{2}})", text, flags=re.IGNORECASE)
    if match is None:
        return None
    collar = _number(match.group(1))
    sleeve = _number(match.group(2))
    if not _in_span(collar, 14, 22) or not _in_span(sleeve, 28, 40):
        return None
    return _Hit(
        "collar-sleeve",
        (Size(collar, INCH_COLLAR_SIZE), Size(sleeve, INCH_SLEEVE_SIZE)),
        0.92,
    )


def _parse_region_number(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    match = re.fullmatch(
        rf"({_REGION_PREFIX})\s*[-:]?\s*({_NUM})", text, flags=re.IGNORECASE
    )
    if match is None:
        return None
    locale = _prefix_locale(match.group(1), region)
    number = _number(match.group(2))
    if product in _FOOTWEAR or (
        product is None and locale is Locale.EU and _in_span(number, 35, 50)
    ):
        return _Hit(
            "regional-number",
            (Size(number, _locale_shoe(locale)),),
            0.9 if product in _FOOTWEAR else 0.7,
        )
    if product in _DRESS_LIKE or product is None:
        score = 0.92 if product in _DRESS_LIKE else 0.75
        return _Hit(
            "regional-number",
            (
                Size(
                    number,
                    _locale_dress(locale if locale is not Locale.FR else Locale.EU),
                ),
            ),
            score,
        )
    if product in _BOTTOMS and locale in {Locale.UK, Locale.US, Locale.AU}:
        return _Hit("regional-number", (Size(number, INCH_WAIST_SIZE),), 0.8)
    return _Hit(
        "regional-number",
        (
            Size(
                number, _locale_dress(locale if locale is not Locale.FR else Locale.EU)
            ),
        ),
        0.55,
    )


def _parse_bare_number(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    if re.fullmatch(_NUM, text) is None:
        return None
    number = _number(text)
    if product in _FOOTWEAR:
        return _Hit("bare-number", (Size(number, _locale_shoe(region)),), 0.72)
    if product == ProductType.DRESS_SHIRTS and _in_span(number, 14, 22):
        unit = (
            INCH_COLLAR_SIZE
            if region in {Locale.UK, Locale.US, Locale.AU}
            else CM_COLLAR_SIZE
        )
        return _Hit("bare-number", (Size(number, unit),), 0.7)
    if product in _BOTTOMS and _in_span(number, 24, 44):
        unit = (
            INCH_WAIST_SIZE
            if region in {Locale.UK, Locale.US, Locale.AU}
            else CM_WAIST_SIZE
        )
        return _Hit("bare-number", (Size(number, unit),), 0.62)
    if product in _DRESS_LIKE or product is None:
        return _Hit(
            "bare-number",
            (
                Size(
                    number,
                    _locale_dress(region if region is not Locale.FR else Locale.EU),
                ),
            ),
            0.7 if product in _DRESS_LIKE else 0.45,
        )
    return None


def _parse_bra(text: str, region: Locale, product: ProductType | None) -> _Hit | None:
    match = re.fullmatch(rf"({_NUM})\s*([A-Z]{{1,3}})", text, flags=re.IGNORECASE)
    if match is None:
        return None
    try:
        cup = normalize_cup_token(match.group(2))
    except ValueError:
        return None
    if cup not in CUP_TOKENS or cup in {"S", "R", "L"}:
        return None
    band = _number(match.group(1))
    if not _in_span(band, 28, 56):
        return None
    score = 0.95 if product is ProductType.BRAS else 0.8 if product is None else 0.4
    if (
        product is not None
        and product is not ProductType.BRAS
        and product not in _DRESS_LIKE
    ):
        return None
    band_unit = (
        UK_BAND_SIZE if region in {Locale.UK, Locale.US, Locale.AU} else UK_BAND_SIZE
    )
    return _Hit("bra", (Size(band, band_unit), Size(cup, UK_CUP_SIZE)), score)


def _parse_waist_leg(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    match = re.fullmatch(
        rf"(?:[WL]\s*)?({_NUM})\s*(?:[xX/]|[WL])\s*(?:[WL]\s*)?({_NUM})",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    waist = _number(match.group(1))
    leg = _number(match.group(2))
    if not _in_span(waist, 24, 50) or not _in_span(leg, 24, 42):
        return None
    if (
        product is not None
        and product not in _BOTTOMS
        and product is not ProductType.SHORTS
    ):
        return None
    score = 0.93 if product in _BOTTOMS else 0.8
    return _Hit(
        "waist-leg",
        (Size(waist, INCH_WAIST_SIZE), Size(leg, INCH_TROUSERS_INSEAM)),
        score,
    )


def _parse_waist_length(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    match = re.fullmatch(rf"({_NUM})\s*([SRL])", text, flags=re.IGNORECASE)
    if match is None:
        return None
    waist = _number(match.group(1))
    if not _in_span(waist, 24, 50):
        return None
    if product is not None and product not in _BOTTOMS:
        return None
    code = {"S": "short", "R": "regular", "L": "long"}[match.group(2).upper()]
    score = 0.9 if product in _BOTTOMS else 0.74
    return _Hit(
        "waist-length",
        (Size(waist, INCH_WAIST_SIZE), Size(code, TROUSER_LENGTH_SIZE)),
        score,
    )


def _parse_proportion(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    key = text.casefold()
    mapping = {
        "extra tall": "extra-tall",
        "tall": "tall",
        "petite": "petite",
        "pt": "petite",
    }
    token = mapping.get(key)
    if token is None:
        embedded = re.fullmatch(
            rf"{_NUM}\s+(extra\s+tall|tall|petite|pt)", text, flags=re.IGNORECASE
        )
        if embedded is None:
            return None
        token = mapping[embedded.group(1).casefold()]
        number = _number(embedded.group(0).split()[0])
        dress = Size(
            number, _locale_dress(region if region is not Locale.FR else Locale.EU)
        )
        return _Hit("proportion", (dress, Size(token, PROPORTION_SIZE)), 0.86)
    return _Hit("proportion", (Size(token, PROPORTION_SIZE),), 0.9)


def _parse_length_word(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    key = text.casefold()
    words = {
        "extra short": "extra-short",
        "short": "short",
        "regular": "regular",
        "standard": "regular",
        "long": "long",
        "extra long": "extra-long",
    }
    token = words.get(key)
    if token is None:
        return None
    if product in _TOPS:
        return _Hit("length-word", (Size(token, TOP_LENGTH_SIZE),), 0.84)
    if product in _BOTTOMS or product is None:
        return _Hit(
            "length-word",
            (Size(token, TROUSER_LENGTH_SIZE),),
            0.8 if product in _BOTTOMS else 0.55,
        )
    return None


def _parse_shoe_width(
    text: str, region: Locale, product: ProductType | None
) -> _Hit | None:
    letter = re.fullmatch(r"([DEFGH])(?:\s*\(.*\))?", text, flags=re.IGNORECASE)
    words = re.fullmatch(
        r"(extra\s*wide|wide|narrow|standard|medium)(?:\s+fit)?",
        text,
        flags=re.IGNORECASE,
    )
    sized = re.fullmatch(
        rf"({_REGION_PREFIX})?\s*({_NUM})\s+(extra\s*wide|wide|narrow|standard|medium|[DEFGH])(?:\s+fit)?",
        text,
        flags=re.IGNORECASE,
    )
    if (
        product is not None
        and product not in _FOOTWEAR
        and sized is None
        and letter is None
        and words is None
    ):
        return None
    if sized:
        locale = _prefix_locale(sized.group(1) or region.value, region)
        width_raw = sized.group(3)
        token = _SHOE_WIDTH_LETTER.get(
            width_raw.upper(),
            width_raw.casefold().replace(" ", "-").replace("medium", "standard"),
        )
        if token == "extra-wide" or token.replace(" ", "") == "extrawide":
            token = "extra-wide"
        score = 0.9 if product in _FOOTWEAR else 0.7
        return _Hit(
            "shoe-width",
            (
                Size(_number(sized.group(2)), _locale_shoe(locale)),
                Size(token, SHOE_WIDTH_SIZE),
            ),
            score,
        )
    if words and (product in _FOOTWEAR or product is None):
        token = words.group(1).casefold().replace(" ", "")
        token = {"extrawide": "extra-wide", "medium": "standard"}.get(token, token)
        return _Hit(
            "shoe-width",
            (Size(token, SHOE_WIDTH_SIZE),),
            0.88 if product in _FOOTWEAR else 0.6,
        )
    if letter and (product in _FOOTWEAR or product is None):
        return _Hit(
            "shoe-width",
            (Size(_SHOE_WIDTH_LETTER[letter.group(1).upper()], SHOE_WIDTH_SIZE),),
            0.84 if product in _FOOTWEAR else 0.5,
        )
    return None


_AGE_UNITS = (AGE_MONTHS_SIZE, AGE_YEARS_SIZE)


_AGE_UNIT_WORD = re.compile(
    r"\d\s*(?:months?|mths?|mth|m|years?|yrs?|yr|y)\b",
    re.IGNORECASE,
)


def _parse_age(text: str, region: Locale, product: ProductType | None) -> _Hit | None:
    if _AGE_UNIT_WORD.search(text) is None:
        return None
    for unit in _AGE_UNITS:
        try:
            size = Size(text, unit)
        except ValueError:
            continue
        return _Hit("age", (size,), 0.93)
    return None


_PARSERS = (
    _parse_regions,
    _parse_numbered_fit,
    _parse_collar_sleeve,
    _parse_from_units,
    _parse_age,
    _parse_waist_leg,
    _parse_waist_length,
    _parse_bra,
    _parse_shoe_width,
    _parse_proportion,
    _parse_length_word,
    _parse_region_number,
    _parse_bare_number,
)


def _preferred(
    source: Locale, preferred_regions: Sequence[Locale] | None
) -> tuple[Locale, ...]:
    if not preferred_regions:
        return (source,)
    resolved = tuple(
        _require_locale(item, name="preferred_regions") for item in preferred_regions
    )
    return resolved


def _length_unit_for_region(region: Locale) -> str:
    return "cm" if region in {Locale.EU, Locale.FR} else "in"


def _render_label(size: Size, region: Locale) -> str:
    token = str(size.raw)
    if size.size_type.slug in {"age-months", "age-years"}:
        return label_display(size.size_type, token)
    words = _REGION_WORDS.get(token, {})
    return words.get(region, label_display(size.size_type, token))


def _same_measurement(left: Size, right: Size) -> bool:
    return left.size_type.slug == right.size_type.slug


def encode_size_description(
    values: Iterable[Size],
    source_region: Locale,
    preferred_regions: Sequence[Locale] | None = None,
    product_type: ProductType | None = None,
    format: str | None = None,
) -> EncodedSizeDescription:
    """Join size values into one readable string.

    ``source_region`` is the region assumed for a size whose unit is universal.
    ``preferred_regions`` picks which regional value to keep when several
    regions describe the same size type, and how to word label sizes. Chart
    sizes are not converted onto a chart. Length values move between inches
    and centimetres when the preferred region uses the other unit. An empty
    ``preferred_regions`` reuses ``source_region``.
    """
    source = _require_locale(source_region, name="source_region")
    order = _preferred(source, preferred_regions)
    product = _require_product_type(product_type)
    incoming = tuple(values)
    chosen, discarded = _choose_values(incoming, order, source)
    if format is not None and format not in _ENCODERS:
        raise ValueError(f"Unknown size description format {format!r}.")
    encoder_id = format or _guess_format(chosen, product)
    if encoder_id is None or not chosen:
        return EncodedSizeDescription(
            "",
            None,
            0.0,
            (),
            discarded
            + tuple(DiscardedToken(item.display(), "unrecognised") for item in chosen),
        )
    text, used, extra = _ENCODERS[encoder_id](chosen, order[0], source)
    unused = [item for item in chosen if item not in used]
    discarded = (
        discarded
        + extra
        + tuple(DiscardedToken(item.display(), "unused") for item in unused)
    )
    confidence = (
        1.0
        if format
        else (0.9 if len(_candidate_formats(chosen, product)) == 1 else 0.65)
    )
    return EncodedSizeDescription(text, encoder_id, confidence, used, discarded)


def _choose_values(
    values: tuple[Size, ...], order: tuple[Locale, ...], source: Locale
) -> tuple[tuple[Size, ...], tuple[DiscardedToken, ...]]:
    grouped: dict[str, list[Size]] = {}
    for size in values:
        grouped.setdefault(size.size_type.slug, []).append(size)
    kept: list[Size] = []
    discarded: list[DiscardedToken] = []
    for group in grouped.values():
        if len(group) == 1:
            kept.append(_maybe_convert_length(group[0], order[0]))
            continue
        winner = _prefer(group, order, source)
        kept.append(_maybe_convert_length(winner, order[0]))
        for other in group:
            if other is not winner:
                discarded.append(DiscardedToken(other.display(), "duplicate"))
    return tuple(kept), tuple(discarded)


def _prefer(group: list[Size], order: tuple[Locale, ...], source: Locale) -> Size:
    def rank(size: Size) -> tuple[int, int]:
        locale = size.size_unit.locale
        if locale is Locale.UNIVERSAL:
            locale = source
        try:
            return (order.index(locale), 0)
        except ValueError:
            return (len(order), 0)

    return sorted(group, key=rank)[0]


def _maybe_convert_length(size: Size, region: Locale) -> Size:
    if size.size_type.family is not SizeFamily.LENGTH or not size.size_unit.length_unit:
        return size
    wanted = _length_unit_for_region(region)
    if size.size_unit.length_unit == wanted:
        return size
    target = size_unit_for_length_unit(size.size_type, wanted)
    converted = size.convert(target, demographic=_length_demographic())
    return converted.size


def _length_demographic() -> Demographic:
    return Demographic(AgeGroup.ADULT, Gender.UNISEX)


def _candidate_formats(
    sizes: tuple[Size, ...], product: ProductType | None
) -> tuple[str, ...]:
    slugs = {size.size_type.slug for size in sizes}
    found: list[str] = []
    if "waist" in slugs and "trousers-inseam" in slugs:
        found.append("waist-leg")
    if "waist" in slugs and "trouser-length" in slugs:
        found.append("waist-length")
    if "band-size" in slugs and "cup-size" in slugs:
        found.append("bra")
    if product in _FOOTWEAR and ("adult-shoe" in slugs or "shoe-width" in slugs):
        found.append("shoe")
    if slugs <= {"age-months", "age-years"} and slugs:
        found.append("age")
    if "proportion" in slugs and slugs <= {"proportion", "dress"}:
        found.append("proportion")
    if slugs <= {"dress"} or (product in _DRESS_LIKE and "dress" in slugs):
        found.append("regional-number")
    if not found and slugs:
        found.append("pieces")
    return tuple(found)


def _guess_format(sizes: tuple[Size, ...], product: ProductType | None) -> str | None:
    options = _candidate_formats(sizes, product)
    return options[0] if options else None


def _encode_waist_leg(sizes: tuple[Size, ...], region: Locale, source: Locale):
    waist = next(size for size in sizes if size.size_type.slug == "waist")
    leg = next(size for size in sizes if size.size_type.slug == "trousers-inseam")
    waist_in = _as_inches(waist)
    leg_in = _as_inches(leg)
    return (
        f"{format_raw(waist_in.raw)}/{format_raw(leg_in.raw)}",
        (waist_in, leg_in),
        (),
    )


def _encode_waist_length(sizes: tuple[Size, ...], region: Locale, source: Locale):
    waist = next(size for size in sizes if size.size_type.slug == "waist")
    length = next(size for size in sizes if size.size_type.slug == TROUSER_LENGTH.slug)
    waist_in = _as_inches(waist)
    code = _TROUSER_CODE.get(str(length.raw), _render_label(length, region))
    return f"{format_raw(waist_in.raw)}{code}", (waist_in, length), ()


def _encode_bra(sizes: tuple[Size, ...], region: Locale, source: Locale):
    band = next(size for size in sizes if size.size_type.slug == "band-size")
    cup = next(size for size in sizes if size.size_type.slug == "cup-size")
    return (
        f"{format_raw(band.raw) if isinstance(band.raw, Decimal) else band.raw}{cup.display()}",
        (band, cup),
        (),
    )


def _encode_shoe(sizes: tuple[Size, ...], region: Locale, source: Locale):
    shoe = next(
        (size for size in sizes if size.size_type.family is SizeFamily.SHOE_SIZE), None
    )
    width = next(
        (size for size in sizes if size.size_type.slug == SHOE_WIDTH.slug), None
    )
    parts: list[str] = []
    used: list[Size] = []
    if shoe is not None:
        parts.append(shoe.display())
        used.append(shoe)
    if width is not None:
        parts.append(_render_label(width, region))
        used.append(width)
    return " ".join(parts), tuple(used), ()


def _encode_age(sizes: tuple[Size, ...], region: Locale, source: Locale):
    age = next(
        size for size in sizes if size.size_type.slug in {"age-months", "age-years"}
    )
    return age.display(), (age,), ()


def _encode_proportion(sizes: tuple[Size, ...], region: Locale, source: Locale):
    proportion = next(size for size in sizes if size.size_type.slug == PROPORTION.slug)
    dress = next((size for size in sizes if size.size_type.slug == "dress"), None)
    label = _render_label(proportion, region)
    if dress is None:
        return label, (proportion,), ()
    return f"{dress.display()} {label}", (dress, proportion), ()


def _encode_regional(sizes: tuple[Size, ...], region: Locale, source: Locale):
    dress = next(size for size in sizes if size.size_type.slug == "dress")
    return dress.display(), (dress,), ()


def _encode_pieces(sizes: tuple[Size, ...], region: Locale, source: Locale):
    parts = []
    for size in sizes:
        if size.size_type.family is SizeFamily.LABEL:
            parts.append(_render_label(size, region))
        else:
            parts.append(size.display())
    return " ".join(parts), sizes, ()


def _as_inches(size: Size) -> Size:
    if size.size_unit.length_unit == "in":
        return size
    if size.size_unit.length_unit == "cm":
        return size.convert(
            size_unit_for_length_unit(size.size_type, "in"),
            demographic=_length_demographic(),
        ).size
    return size


_ENCODERS = {
    "waist-leg": _encode_waist_leg,
    "waist-length": _encode_waist_length,
    "bra": _encode_bra,
    "shoe": _encode_shoe,
    "age": _encode_age,
    "proportion": _encode_proportion,
    "regional-number": _encode_regional,
    "pieces": _encode_pieces,
}
