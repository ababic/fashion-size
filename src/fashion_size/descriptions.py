"""Recognise feed size strings and render a series of sizes back to text.

Importing this module compiles the format patterns. ``fashion_size`` itself
does not import it, so the patterns stay out of memory until these APIs run.

A product type's family decides how an unlabelled number is read. Each size
type names the product types it belongs with, and a label size type owns its
own tokens and wording. Chart sizes (dress, shoe, waist size, chest size,
band, cup) stay in the region they were written in. Length measurements can
move between centimetres and inches. Nothing here consults a conversion chart
except that length-unit change.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from fashion_size.demographics import AgeGroup, Demographic, Gender
from fashion_size.product_types import ProductType, ProductTypeFamily
from fashion_size.types import (
    ADULT_SHOE,
    AGE_MONTHS,
    AGE_MONTHS_SIZE,
    AGE_YEARS,
    AGE_YEARS_SIZE,
    BAND_SIZE,
    CHEST_SIZE,
    CM_COLLAR_SIZE,
    CM_WAIST_SIZE,
    CUP_SIZE,
    CUP_TOKENS,
    DRESS,
    INCH_COLLAR_SIZE,
    INCH_SLEEVE_SIZE,
    INCH_TROUSERS_INSEAM,
    INCH_WAIST_SIZE,
    LETTER,
    PROPORTION,
    PROPORTION_SIZE,
    SHOE_WIDTH,
    SHOE_WIDTH_SIZE,
    SIZE_UNITS,
    TOP_LENGTH_SIZE,
    TROUSER_LENGTH,
    TROUSER_LENGTH_SIZE,
    TROUSERS_INSEAM,
    UK_BAND_SIZE,
    UK_CUP_SIZE,
    WAIST,
    WAIST_SIZE,
    LengthOutOfRangeError,
    Locale,
    Size,
    SizeFamily,
    SizeType,
    SizeUnit,
    format_raw,
    length_value_in_range,
    normalize_cup_token,
    normalize_raw,
    size_unit_for_length_unit,
    size_unit_for_locale,
)

_REGION_PREFIX = r"(?:UK|EU|EUR|US|AU|FR)"
_NUM = r"\d{1,2}(?:\.\d)?"
_UNLABELLED_EU_SHOE = (35, 50)
# Shared unit-pattern scores. A marked W/L span adds the width term on top.
_EXPLICIT_SCORE = 0.82
_BARE_SCORE = 0.48
_LOCALE_BONUS = 0.05
_MARKED_BONUS = 0.12
_MARKED_SPAN_BONUS = 0.05
_AMBIGUITY_PENALTY = 0.45
# Feed conventions, tighter than the size type's own inch range.
_FEED_WAIST_INCHES = (24, 50)
_UK_BRA_BAND_INCHES = (28, 56)

# Context that looks like a size token but is a quantity, a year, a collection
# name, or a garment phrase. A recognition match inside one of these is not a size.
_EXCEPTION_PATTERNS = (
    re.compile(r"\b\d+\s*-?\s*packs?\b", re.IGNORECASE),
    re.compile(r"\bpacks?\s+of\s+\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:19|20)\d{2}\b"),
    re.compile(r"\bpetite\s+(?:edit|collection|range|line)\b", re.IGNORECASE),
    re.compile(r"\b(?:extra[\s-]+)?(?:long|short)\s+sleeves?\b", re.IGNORECASE),
)
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
_FIT_WORDS = {
    "r": "regular",
    "s": "short",
    "l": "long",
    "t": "tall",
    "x": "extra-tall",
    "petite": "petite",
    "tall": "tall",
    "extra tall": "extra-tall",
}


class SizeDescriptionFormat(StrEnum):
    """Format ids returned by decode and encode. Values are the public strings."""

    REGIONS = "regions"
    NUMBERED_FIT = "numbered-fit"
    COLLAR_SLEEVE = "collar-sleeve"
    UNIT_PATTERNS = "unit-patterns"
    AGE = "age"
    WAIST_LEG = "waist-leg"
    WAIST_LENGTH = "waist-length"
    BRA = "bra"
    SHOE_WIDTH = "shoe-width"
    PROPORTION = "proportion"
    LENGTH_WORD = "length-word"
    REGIONAL_NUMBER = "regional-number"
    BARE_NUMBER = "bare-number"
    SHOE = "shoe"
    PIECES = "pieces"


@dataclass(frozen=True, slots=True)
class _CrossTypePenalty:
    """Score subtracted when one size type is easily read as another.

    ``when_matches`` selects the product type named in ``product``. When it is
    false, every other product type is penalised, including no product type.
    An empty ``raw`` set applies to every value.
    """

    size_type: SizeType
    product: ProductType
    when_matches: bool
    raw: frozenset[object]
    penalty: float


# Cup S/M/L is a letter size unless the product is a bra. A letter size on a
# bra is a cup. These sit next to the reader because they compare two size types.
_CROSS_TYPE_PENALTIES = (
    _CrossTypePenalty(
        CUP_SIZE,
        ProductType.BRAS,
        False,
        frozenset({"S", "M", "L"}),
        _AMBIGUITY_PENALTY,
    ),
    _CrossTypePenalty(
        LETTER,
        ProductType.BRAS,
        True,
        frozenset(),
        _AMBIGUITY_PENALTY,
    ),
)


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


def _in_span(value: Decimal, low: int | Decimal, high: int | Decimal) -> bool:
    return Decimal(low) <= value <= Decimal(high)


def _cross_type_penalty(
    size_type: SizeType, raw: object, product: ProductType | None
) -> float:
    penalty = 0.0
    for rule in _CROSS_TYPE_PENALTIES:
        if size_type is not rule.size_type:
            continue
        if (product is rule.product) is not rule.when_matches:
            continue
        if rule.raw and raw not in rule.raw:
            continue
        penalty -= rule.penalty
    return penalty


def _explicit_word(text: str, unit: SizeUnit) -> bool:
    """Whether ``text`` is one whole explicit recognition, not a short code.

    A bare ``R`` is a trouser-length token only after a digit, so the letter
    pattern does not match the cell on its own. ``Regular`` does.
    """
    return any(
        entry.explicit
        and not entry.marked
        and re.fullmatch(entry.expression, text, flags=re.IGNORECASE)
        for entry in unit.recognition
    )


def _number(text: str) -> Decimal:
    return normalize_raw(text)


class SizeDescription:
    """Read one feed string, and join size values back into one string.

    The product type's family and profile choose the reading. Size types own
    the recognition patterns, the product types they belong with, and label
    wording.
    """

    def decode(
        self,
        value: str,
        source_region: Locale,
        product_type: ProductType | None = None,
    ) -> DecodedSizeDescription:
        region = _require_locale(source_region, name="source_region")
        product = _require_product_type(product_type)
        text = " ".join((value or "").strip().split())
        if _PURE_RANGE.fullmatch(text):
            return DecodedSizeDescription(
                (), None, 0.0, (DiscardedToken(text, "range"),), ()
            )
        if not text:
            return DecodedSizeDescription((), None, 0.0, (), ())
        readers = (
            self._regions,
            self._numbered_fit,
            self._collar_sleeve,
            self._from_units,
            self._age,
            self._waist_leg,
            self._waist_length,
            self._bra,
            self._shoe_width,
            self._proportion,
            self._length_word,
            self._region_number,
            self._bare_number,
        )
        hits = [
            hit for reader in readers if (hit := reader(text, region, product)) is not None
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

    def encode(
        self,
        values: Iterable[Size],
        source_region: Locale,
        preferred_regions: Sequence[Locale] | None = None,
        product_type: ProductType | None = None,
        format: str | None = None,
    ) -> EncodedSizeDescription:
        source = _require_locale(source_region, name="source_region")
        order = self._preferred(source, preferred_regions)
        product = _require_product_type(product_type)
        incoming = tuple(values)
        chosen, discarded = self._choose_values(incoming, order, source)
        writers = {
            SizeDescriptionFormat.WAIST_LEG: self._write_waist_leg,
            SizeDescriptionFormat.WAIST_LENGTH: self._write_waist_length,
            SizeDescriptionFormat.BRA: self._write_bra,
            SizeDescriptionFormat.SHOE: self._write_shoe,
            SizeDescriptionFormat.AGE: self._write_age,
            SizeDescriptionFormat.PROPORTION: self._write_proportion,
            SizeDescriptionFormat.REGIONAL_NUMBER: self._write_regional,
            SizeDescriptionFormat.PIECES: self._write_pieces,
        }
        if format is not None and format not in writers:
            raise ValueError(f"Unknown size description format {format!r}.")
        encoder_id = format or self._guess_format(chosen, product)
        if encoder_id is None or not chosen:
            return EncodedSizeDescription(
                "",
                None,
                0.0,
                (),
                discarded
                + tuple(
                    DiscardedToken(item.display(), "unrecognised") for item in chosen
                ),
            )
        text, used, extra = writers[encoder_id](chosen, order[0], source)
        out_of_range = {item.text for item in extra if item.reason == "out-of-range"}
        unused = [
            item
            for item in chosen
            if item not in used and item.display() not in out_of_range
        ]
        discarded = (
            discarded
            + extra
            + tuple(DiscardedToken(item.display(), "unused") for item in unused)
        )
        confidence = (
            1.0
            if format
            else (0.9 if len(self._candidate_formats(chosen, product)) == 1 else 0.65)
        )
        return EncodedSizeDescription(text, encoder_id, confidence, used, discarded)

    def _from_units(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        """Find size values by each unit's own recognition patterns."""
        found: list[tuple[int, int, float, Size]] = []
        chart_region = self._chart_locale(region)
        for unit in SIZE_UNITS:
            for entry, pattern in zip(
                unit.recognition, unit.recognition_patterns(), strict=True
            ):
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
                    if (
                        unit.size_type.family is SizeFamily.CUP_SIZE
                        and not self._cup_span_ok(text, match)
                    ):
                        continue
                    built = self._size_from_unit(
                        unit,
                        match.group("value"),
                        region=region,
                        chart_region=chart_region,
                        product=product,
                        explicit=entry.explicit,
                    )
                    if built is None:
                        continue
                    size, score = built
                    if entry.marked:
                        score += _MARKED_BONUS
                        span = unit.size_type.length_range
                        if span is not None:
                            width = span.stop_inches - span.start_inches
                            score += _MARKED_SPAN_BONUS / float(width)
                    found.append((match.start(), match.end(), score, size))
        chosen = _pick_nonoverlapping(found)
        if not chosen:
            return None
        sizes = tuple(item[3] for item in chosen)
        score = sum(item[2] for item in chosen) / len(chosen)
        covered = sum(item[1] - item[0] for item in chosen)
        if covered < len(text.replace(" ", "")) / 2 and len(sizes) == 1:
            score -= 0.15
        return _Hit(SizeDescriptionFormat.UNIT_PATTERNS, sizes, max(score, 0.2))

    def _size_from_unit(
        self,
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
        if not explicit and not unit.size_type.allows_bare_feed_value(product):
            return None
        score = _EXPLICIT_SCORE if explicit else _BARE_SCORE
        score += unit.size_type.affinity_adjustment(product)
        score += _cross_type_penalty(unit.size_type, size.raw, product)
        if unit.locale is chart_region or unit.locale is region:
            score += _LOCALE_BONUS
        return size, score

    def _cup_span_ok(self, text: str, match: re.Match[str]) -> bool:
        """A cup letter counts on its own, or immediately after a band number."""
        before = text[: match.start()].strip()
        after = text[match.end() :].strip()
        if not before and not after:
            return True
        return bool(re.search(r"\d$", before)) and not after

    def _regions(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        """Every labelled region in one cell, skipping a range such as ``UK 8-10``."""
        discarded: list[DiscardedToken] = []
        found: list[tuple[int, Size]] = []
        seen: set[tuple[str, Locale]] = set()

        def add(locale: Locale, raw: str, at: int) -> None:
            number = _number(raw)
            unit = self._chart_unit_for_number(locale, number, product)
            key = (unit.size_type.slug, unit.locale)
            if key in seen:
                return
            seen.add(key)
            found.append((at, Size(number, unit)))

        for match in _REGION_VALUE.finditer(text):
            if _RANGE_TAIL.match(text[match.end() :]):
                discarded.append(
                    DiscardedToken(
                        match.group(0) + text[match.end() :].split()[0], "range"
                    )
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
            return _Hit(SizeDescriptionFormat.REGIONS, (), 0.2, tuple(discarded))
        score = 0.98 if discarded else (0.96 if len(sizes) > 1 else 0.7)
        return _Hit(SizeDescriptionFormat.REGIONS, sizes, score, tuple(discarded))

    def _numbered_fit(
        self, text: str, region: Locale, product: ProductType | None
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
        proportion = _FIT_WORDS.get(word)
        if word in {"r", "s", "l"} and _in_span(number, *_FEED_WAIST_INCHES) and (
            product is None or not product.family.accepts_fit_code
        ):
            return None
        chest = None if product is None else product.profile.chest_span
        if chest is not None and _in_span(number, *chest):
            chart = self._chart_unit_for_number(region, number, product)
            label = Size(proportion or "regular", PROPORTION_SIZE)
            return _Hit(SizeDescriptionFormat.NUMBERED_FIT, (Size(number, chart), label), 0.9)
        if word == "full length":
            return _Hit(
                SizeDescriptionFormat.NUMBERED_FIT,
                (self._dress_size(number, region), Size("long", TOP_LENGTH_SIZE)),
                0.88,
            )
        if proportion is None:
            return None
        return _Hit(
            SizeDescriptionFormat.NUMBERED_FIT,
            (self._dress_size(number, region), Size(proportion, PROPORTION_SIZE)),
            0.88,
        )

    def _collar_sleeve(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        """``15.5/34`` on a shirt is collar inches and sleeve inches."""
        span = None if product is None else product.profile.collar_sleeve
        if span is None:
            return None
        match = re.fullmatch(rf"({_NUM})\s*[/x]\s*(\d{{2}})", text, flags=re.IGNORECASE)
        if match is None:
            return None
        collar = _number(match.group(1))
        sleeve = _number(match.group(2))
        collar_low, collar_high, sleeve_low, sleeve_high = span
        if not _in_span(collar, collar_low, collar_high) or not _in_span(
            sleeve, sleeve_low, sleeve_high
        ):
            return None
        return _Hit(
            SizeDescriptionFormat.COLLAR_SLEEVE,
            (Size(collar, INCH_COLLAR_SIZE), Size(sleeve, INCH_SLEEVE_SIZE)),
            0.92,
        )

    def _region_number(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        match = re.fullmatch(
            rf"({_REGION_PREFIX})\s*[-:]?\s*({_NUM})", text, flags=re.IGNORECASE
        )
        if match is None:
            return None
        locale = _prefix_locale(match.group(1), region)
        number = _number(match.group(2))
        if self._reads_as_shoe(product, locale, number):
            return _Hit(
                SizeDescriptionFormat.REGIONAL_NUMBER,
                (Size(number, self._shoe_unit(locale)),),
                0.9 if product is not None and product.family.reads_shoe_size else 0.7,
            )
        if product is None or product.family.reads_dress_size:
            score = (
                0.92 if product is not None and product.family.reads_dress_size else 0.75
            )
            return _Hit(
                SizeDescriptionFormat.REGIONAL_NUMBER,
                (self._dress_size(number, locale),),
                score,
            )
        if (
            product.family is ProductTypeFamily.BOTTOMS
            and locale in {Locale.UK, Locale.US, Locale.AU}
        ):
            return _Hit(
                SizeDescriptionFormat.REGIONAL_NUMBER,
                (Size(number, INCH_WAIST_SIZE),),
                0.8,
            )
        return _Hit(
            SizeDescriptionFormat.REGIONAL_NUMBER,
            (self._dress_size(number, locale),),
            0.55,
        )

    def _bare_number(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        if re.fullmatch(_NUM, text) is None:
            return None
        number = _number(text)
        if product is not None and product.family.reads_shoe_size:
            return _Hit(SizeDescriptionFormat.BARE_NUMBER, (Size(number, self._shoe_unit(region)),), 0.72)
        collar = None if product is None else product.profile.collar_span
        if collar is not None and _in_span(number, *collar):
            unit = (
                INCH_COLLAR_SIZE
                if region in {Locale.UK, Locale.US, Locale.AU}
                else CM_COLLAR_SIZE
            )
            return _Hit(SizeDescriptionFormat.BARE_NUMBER, (Size(number, unit),), 0.7)
        waist = None if product is None else product.family.bare_waist_span
        if waist is not None and _in_span(number, *waist):
            unit = (
                INCH_WAIST_SIZE
                if region in {Locale.UK, Locale.US, Locale.AU}
                else CM_WAIST_SIZE
            )
            return _Hit(SizeDescriptionFormat.BARE_NUMBER, (Size(number, unit),), 0.62)
        if product is None or product.family.reads_dress_size:
            return _Hit(
                SizeDescriptionFormat.BARE_NUMBER,
                (self._dress_size(number, region),),
                0.7 if product is not None and product.family.reads_dress_size else 0.45,
            )
        return None

    def _bra(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
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
        if not _in_span(band, *_UK_BRA_BAND_INCHES):
            return None
        if product is not None and product.family is ProductTypeFamily.BRAS:
            score = 0.95
        elif product is None:
            score = 0.8
        elif product.family.reads_dress_size:
            score = 0.4
        else:
            return None
        # Feed bra strings are read as a UK inch band. The cup letter is universal.
        return _Hit(
            SizeDescriptionFormat.BRA,
            (Size(band, UK_BAND_SIZE), Size(cup, UK_CUP_SIZE)),
            score,
        )

    def _waist_leg(
        self, text: str, region: Locale, product: ProductType | None
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
        leg_low, leg_high = TROUSERS_INSEAM.length_inch_bounds()
        if not _in_span(waist, *_FEED_WAIST_INCHES) or not _in_span(
            leg, leg_low, leg_high
        ):
            return None
        if product is not None and product.family is not ProductTypeFamily.BOTTOMS:
            return None
        score = 0.93 if product is not None else 0.8
        return _Hit(
            SizeDescriptionFormat.WAIST_LEG,
            (Size(waist, INCH_WAIST_SIZE), Size(leg, INCH_TROUSERS_INSEAM)),
            score,
        )

    def _waist_length(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        match = re.fullmatch(rf"({_NUM})\s*([SRL])", text, flags=re.IGNORECASE)
        if match is None:
            return None
        waist = _number(match.group(1))
        if not _in_span(waist, *_FEED_WAIST_INCHES):
            return None
        if product is not None and product.family is not ProductTypeFamily.BOTTOMS:
            return None
        code = {"S": "short", "R": "regular", "L": "long"}[match.group(2).upper()]
        score = 0.9 if product is not None else 0.74
        return _Hit(
            SizeDescriptionFormat.WAIST_LENGTH,
            (Size(waist, INCH_WAIST_SIZE), Size(code, TROUSER_LENGTH_SIZE)),
            score,
        )

    def _proportion(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        if _explicit_word(text, PROPORTION_SIZE):
            return _Hit(
                SizeDescriptionFormat.PROPORTION,
                (Size(text, PROPORTION_SIZE),),
                0.9,
            )
        for entry in PROPORTION_SIZE.recognition:
            if not entry.explicit or entry.marked:
                continue
            embedded = re.fullmatch(
                rf"({_NUM})\s+{entry.expression}", text, flags=re.IGNORECASE
            )
            if embedded is None:
                continue
            return _Hit(
                SizeDescriptionFormat.PROPORTION,
                (
                    self._dress_size(_number(embedded.group(1)), region),
                    Size(embedded.group("value"), PROPORTION_SIZE),
                ),
                0.86,
            )
        return None

    def _length_word(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        if product is not None and product.family is ProductTypeFamily.TOPS:
            unit = TOP_LENGTH_SIZE
            score = 0.84
        elif product is None or product.family is ProductTypeFamily.BOTTOMS:
            unit = TROUSER_LENGTH_SIZE
            score = 0.8 if product is not None else 0.55
        else:
            return None
        if not _explicit_word(text, unit):
            return None
        return _Hit(SizeDescriptionFormat.LENGTH_WORD, (Size(text, unit),), score)

    def _shoe_width(
        self, text: str, region: Locale, product: ProductType | None
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
            and not product.family.reads_shoe_size
            and sized is None
            and letter is None
            and words is None
        ):
            return None
        if sized:
            locale = _prefix_locale(sized.group(1) or region.value, region)
            score = 0.9 if product is not None and product.family.reads_shoe_size else 0.7
            return _Hit(
                SizeDescriptionFormat.SHOE_WIDTH,
                (
                    Size(_number(sized.group(2)), self._shoe_unit(locale)),
                    Size(sized.group(3), SHOE_WIDTH_SIZE),
                ),
                score,
            )
        if words and (product is None or product.family.reads_shoe_size):
            return _Hit(
                SizeDescriptionFormat.SHOE_WIDTH,
                (Size(words.group(1), SHOE_WIDTH_SIZE),),
                0.88 if product is not None and product.family.reads_shoe_size else 0.6,
            )
        if letter and (product is None or product.family.reads_shoe_size):
            return _Hit(
                SizeDescriptionFormat.SHOE_WIDTH,
                (Size(letter.group(1), SHOE_WIDTH_SIZE),),
                0.84 if product is not None and product.family.reads_shoe_size else 0.5,
            )
        return None

    def _age(
        self, text: str, region: Locale, product: ProductType | None
    ) -> _Hit | None:
        if (
            re.search(
                r"\d\s*(?:months?|mths?|mth|m|years?|yrs?|yr|y)\b",
                text,
                flags=re.IGNORECASE,
            )
            is None
        ):
            return None
        for unit in (AGE_MONTHS_SIZE, AGE_YEARS_SIZE):
            try:
                size = Size(text, unit)
            except ValueError:
                continue
            return _Hit(SizeDescriptionFormat.AGE, (size,), 0.93)
        return None

    def _chart_locale(self, locale: Locale) -> Locale:
        """French feed prefixes use the EU column for description reading."""
        return Locale.EU if locale is Locale.FR else locale

    def _chart_unit(self, size_type: SizeType, locale: Locale) -> SizeUnit:
        return size_unit_for_locale(size_type, self._chart_locale(locale))

    def _shoe_unit(self, locale: Locale) -> SizeUnit:
        return self._chart_unit(ADULT_SHOE, locale)

    def _dress_size(self, number: Decimal, locale: Locale) -> Size:
        return Size(number, self._chart_unit(DRESS, locale))

    def _reads_as_shoe(
        self, product: ProductType | None, locale: Locale, number: Decimal
    ) -> bool:
        """Whether this number is an adult shoe size.

        A footwear product type always is. With no product type, an EU number
        in the shoe span is too. A French prefix is folded onto EU before that
        guess, so a lone ``FR 40`` and a multi-region cell use the same rule.
        """
        if product is not None and product.family.reads_shoe_size:
            return True
        low, high = _UNLABELLED_EU_SHOE
        return (
            product is None
            and self._chart_locale(locale) is Locale.EU
            and _in_span(number, low, high)
        )

    def _chart_unit_for_number(
        self, locale: Locale, number: Decimal, product: ProductType | None
    ) -> SizeUnit:
        if self._reads_as_shoe(product, locale, number):
            return self._shoe_unit(locale)
        chest = None if product is None else product.profile.chest_span
        if chest is not None and _in_span(number, *chest):
            return self._chart_unit(CHEST_SIZE, locale)
        waist = None if product is None else product.family.chart_waist_span
        if waist is not None and _in_span(number, *waist):
            return self._chart_unit(WAIST_SIZE, locale)
        return self._chart_unit(DRESS, locale)

    def _preferred(
        self, source: Locale, preferred_regions: Sequence[Locale] | None
    ) -> tuple[Locale, ...]:
        if not preferred_regions:
            return (source,)
        return tuple(
            _require_locale(item, name="preferred_regions") for item in preferred_regions
        )

    def _choose_values(
        self, values: tuple[Size, ...], order: tuple[Locale, ...], source: Locale
    ) -> tuple[tuple[Size, ...], tuple[DiscardedToken, ...]]:
        grouped: dict[str, list[Size]] = {}
        for size in values:
            grouped.setdefault(size.size_type.slug, []).append(size)
        kept: list[Size] = []
        discarded: list[DiscardedToken] = []
        for group in grouped.values():
            if len(group) == 1:
                chosen = group[0]
                others: tuple[Size, ...] = ()
            else:
                chosen = self._prefer(group, order, source)
                others = tuple(other for other in group if other is not chosen)
            converted = self._maybe_convert_length(chosen, order[0])
            if converted is None:
                discarded.append(DiscardedToken(chosen.display(), "out-of-range"))
            else:
                kept.append(converted)
            for other in others:
                discarded.append(DiscardedToken(other.display(), "duplicate"))
        return tuple(kept), tuple(discarded)

    def _prefer(self, group: list[Size], order: tuple[Locale, ...], source: Locale) -> Size:
        def rank(size: Size) -> tuple[int, int]:
            locale = size.size_unit.locale
            if locale is Locale.UNIVERSAL:
                locale = source
            try:
                return (order.index(locale), 0)
            except ValueError:
                return (len(order), 0)

        return sorted(group, key=rank)[0]

    def _maybe_convert_length(self, size: Size, region: Locale) -> Size | None:
        if size.size_type.family is not SizeFamily.LENGTH or not size.size_unit.length_unit:
            return size
        wanted = "cm" if region in {Locale.EU, Locale.FR} else "in"
        if size.size_unit.length_unit == wanted:
            return size
        target = size_unit_for_length_unit(size.size_type, wanted)
        try:
            return size.convert(target, demographic=_length_demographic()).size
        except LengthOutOfRangeError:
            return None

    def _candidate_formats(
        self, sizes: tuple[Size, ...], product: ProductType | None
    ) -> tuple[SizeDescriptionFormat, ...]:
        found_types = {size.size_type for size in sizes}
        found: list[SizeDescriptionFormat] = []
        if WAIST in found_types and TROUSERS_INSEAM in found_types:
            found.append(SizeDescriptionFormat.WAIST_LEG)
        if WAIST in found_types and TROUSER_LENGTH in found_types:
            found.append(SizeDescriptionFormat.WAIST_LENGTH)
        if BAND_SIZE in found_types and CUP_SIZE in found_types:
            found.append(SizeDescriptionFormat.BRA)
        if (
            product is not None
            and product.family.reads_shoe_size
            and (ADULT_SHOE in found_types or SHOE_WIDTH in found_types)
        ):
            found.append(SizeDescriptionFormat.SHOE)
        if found_types and found_types <= {AGE_MONTHS, AGE_YEARS}:
            found.append(SizeDescriptionFormat.AGE)
        if PROPORTION in found_types and found_types <= {PROPORTION, DRESS}:
            found.append(SizeDescriptionFormat.PROPORTION)
        if found_types <= {DRESS} or (
            product is not None
            and product.family.reads_dress_size
            and DRESS in found_types
        ):
            found.append(SizeDescriptionFormat.REGIONAL_NUMBER)
        if not found and found_types:
            found.append(SizeDescriptionFormat.PIECES)
        return tuple(found)

    def _guess_format(
        self, sizes: tuple[Size, ...], product: ProductType | None
    ) -> SizeDescriptionFormat | None:
        options = self._candidate_formats(sizes, product)
        return options[0] if options else None

    def _write_waist_leg(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        waist = next(size for size in sizes if size.size_type is WAIST)
        leg = next(size for size in sizes if size.size_type is TROUSERS_INSEAM)
        waist_in = _as_inches(waist)
        leg_in = _as_inches(leg)
        discarded: list[DiscardedToken] = []
        if waist_in is None:
            discarded.append(DiscardedToken(waist.display(), "out-of-range"))
        if leg_in is None:
            discarded.append(DiscardedToken(leg.display(), "out-of-range"))
        if waist_in is None or leg_in is None:
            return "", (), tuple(discarded)
        return (
            f"{format_raw(waist_in.raw)}/{format_raw(leg_in.raw)}",
            (waist_in, leg_in),
            (),
        )

    def _write_waist_length(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        waist = next(size for size in sizes if size.size_type is WAIST)
        length = next(size for size in sizes if size.size_type is TROUSER_LENGTH)
        waist_in = _as_inches(waist)
        if waist_in is None:
            return "", (), (DiscardedToken(waist.display(), "out-of-range"),)
        vocabulary = length.size_type.vocabulary
        code = "" if vocabulary is None else vocabulary.shorthand_for(str(length.raw))
        if not code:
            code = length.size_type.label_text(str(length.raw), region)
        return f"{format_raw(waist_in.raw)}{code}", (waist_in, length), ()

    def _write_bra(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        band = next(size for size in sizes if size.size_type is BAND_SIZE)
        cup = next(size for size in sizes if size.size_type is CUP_SIZE)
        band_text = format_raw(band.raw) if isinstance(band.raw, Decimal) else band.raw
        return f"{band_text}{cup.display()}", (band, cup), ()

    def _write_shoe(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        shoe = next(
            (size for size in sizes if size.size_type.family is SizeFamily.SHOE_SIZE),
            None,
        )
        width = next((size for size in sizes if size.size_type is SHOE_WIDTH), None)
        parts: list[str] = []
        used: list[Size] = []
        if shoe is not None:
            parts.append(shoe.display())
            used.append(shoe)
        if width is not None:
            parts.append(width.size_type.label_text(str(width.raw), region))
            used.append(width)
        return " ".join(parts), tuple(used), ()

    def _write_age(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        age = next(
            size for size in sizes if size.size_type in {AGE_MONTHS, AGE_YEARS}
        )
        return age.display(), (age,), ()

    def _write_proportion(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        proportion = next(size for size in sizes if size.size_type is PROPORTION)
        dress = next((size for size in sizes if size.size_type is DRESS), None)
        label = proportion.size_type.label_text(str(proportion.raw), region)
        if dress is None:
            return label, (proportion,), ()
        return f"{dress.display()} {label}", (dress, proportion), ()

    def _write_regional(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        dress = next(size for size in sizes if size.size_type is DRESS)
        return dress.display(), (dress,), ()

    def _write_pieces(
        self, sizes: tuple[Size, ...], region: Locale, source: Locale
    ) -> tuple[str, tuple[Size, ...], tuple[DiscardedToken, ...]]:
        parts = []
        for size in sizes:
            if size.size_type.family is SizeFamily.LABEL:
                parts.append(size.size_type.label_text(str(size.raw), region))
            else:
                parts.append(size.display())
        return " ".join(parts), sizes, ()


def _pick_nonoverlapping(
    found: list[tuple[int, int, float, Size]],
) -> list[tuple[int, int, float, Size]]:
    ordered = sorted(found, key=lambda item: (item[2], item[1] - item[0]), reverse=True)
    chosen: list[tuple[int, int, float, Size]] = []
    for item in ordered:
        if any(not (item[1] <= kept[0] or item[0] >= kept[1]) for kept in chosen):
            continue
        if any(
            kept[3].size_type is item[3].size_type
            and kept[3].size_unit.locale == item[3].size_unit.locale
            for kept in chosen
        ):
            continue
        chosen.append(item)
    chosen.sort(key=lambda item: item[0])
    return chosen


def _overlaps_exception(text: str, start: int, end: int) -> bool:
    for pattern in _EXCEPTION_PATTERNS:
        for found in pattern.finditer(text):
            if found.start() < end and found.end() > start:
                return True
    return False


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


def _length_demographic() -> Demographic:
    return Demographic(AgeGroup.ADULT, Gender.UNISEX)


def _as_inches(size: Size) -> Size | None:
    if size.size_unit.length_unit == "in":
        return size
    if size.size_unit.length_unit == "cm":
        try:
            return size.convert(
                size_unit_for_length_unit(size.size_type, "in"),
                demographic=_length_demographic(),
            ).size
        except LengthOutOfRangeError:
            return None
    return size


_SIZE_DESCRIPTIONS = SizeDescription()


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
    return _SIZE_DESCRIPTIONS.decode(value, source_region, product_type)


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
    return _SIZE_DESCRIPTIONS.encode(
        values,
        source_region,
        preferred_regions=preferred_regions,
        product_type=product_type,
        format=format,
    )
