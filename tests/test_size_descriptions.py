"""Feed size strings: decode into sizes, encode back to text."""

import pytest

from fashion_size.descriptions import decode_size_description, encode_size_description
from fashion_size.product_types import ProductType
from fashion_size.types import (
    AGE_SIZE,
    CM_WAIST_SIZE,
    EU_ADULT_SHOE_SIZE,
    EU_DRESS_SIZE,
    INCH_COLLAR_SIZE,
    INCH_INSIDE_LEG,
    INCH_SHORTS_INSEAM,
    INCH_TROUSERS_INSEAM,
    INCH_WAIST_SIZE,
    PROPORTION_SIZE,
    SHOE_WIDTH_SIZE,
    TOP_LENGTH_SIZE,
    TROUSER_LENGTH_SIZE,
    UK_ADULT_SHOE_SIZE,
    UK_BAND_SIZE,
    UK_CUP_SIZE,
    UK_DRESS_SIZE,
    US_DRESS_SIZE,
    Size,
)


def test_waist_leg_and_length_code():
    decoded = decode_size_description("30/32", "uk", product_type=ProductType.JEANS)
    assert decoded.format_id == "waist-leg"
    assert decoded.confidence >= 0.9
    assert [size.raw for size in decoded.sizes] == [30, 32]
    encoded = encode_size_description(decoded.sizes, "uk")
    assert encoded.text == "30/32"

    length = decode_size_description("30L", "uk", product_type=ProductType.TROUSERS)
    assert length.format_id == "waist-length"
    assert length.sizes[1].raw == "long"
    assert encode_size_description(length.sizes, "uk").text == "30L"


def test_bra_age_proportion_and_shoe_width():
    bra = decode_size_description("32DD", "uk", product_type=ProductType.BRAS)
    assert bra.format_id == "bra"
    assert bra.sizes[1].raw == "DD"

    age = decode_size_description("5-6 yrs", "uk")
    assert age.sizes[0].raw == "5-6y"
    assert age.sizes[0].display() == "5-6 years"

    petite = decode_size_description("Petite", "uk", product_type=ProductType.DRESSES)
    assert petite.sizes[0].raw == "petite"

    width = decode_size_description("UK 6 G", "uk", product_type=ProductType.SHOES)
    assert width.sizes[0].size_unit.locale.value == "uk"
    assert width.sizes[1].raw == "wide"


def test_product_type_changes_a_bare_number():
    dress = decode_size_description("12", "uk", product_type=ProductType.DRESSES)
    shoe = decode_size_description("12", "uk", product_type=ProductType.SHOES)
    assert dress.sizes[0].size_type.slug == "dress"
    assert shoe.sizes[0].size_type.slug == "adult-shoe"


def test_encode_prefers_region_without_converting_charts():
    uk = Size(10, UK_DRESS_SIZE)
    eu = Size(38, EU_DRESS_SIZE)
    encoded = encode_size_description([eu, uk], "eu", preferred_regions=("uk", "eu"))
    assert encoded.text == "UK 10"
    assert encoded.discarded[0].reason == "duplicate"
    assert encoded.discarded[0].text == "EU 38"

    only_eu = encode_size_description([eu], "uk", preferred_regions=("uk", "eu"))
    assert only_eu.text == "EU 38"


def test_units_carry_recognition_patterns():
    patterns = UK_DRESS_SIZE.recognition_patterns()
    assert patterns[0].search("UK 12").group("value") == "12"
    assert any(
        pattern.search('30"') for pattern in INCH_WAIST_SIZE.recognition_patterns()
    )

    missing = decode_size_description("not-a-size", "uk")
    assert missing.sizes == ()
    assert missing.discarded[0].reason == "unrecognised"

    french = encode_size_description(
        [Size("regular", TROUSER_LENGTH_SIZE)],
        "fr",
        preferred_regions=("fr",),
        product_type=ProductType.TROUSERS,
    )
    assert french.text == "Normal"


def _ids(decoded):
    return [(size.size_unit.slug, str(size.raw)) for size in decoded.sizes]


@pytest.mark.parametrize(
    ("raw", "region", "product", "slug", "value"),
    [
        ("UK 10", "eu", ProductType.DRESSES, "uk-dress-size", "10"),
        ("UK-10", "uk", ProductType.DRESSES, "uk-dress-size", "10"),
        ("EUR 38", "uk", ProductType.DRESSES, "eu-dress-size", "38"),
        ("FR 38", "uk", ProductType.DRESSES, "eu-dress-size", "38"),
        ("US 6", "uk", ProductType.DRESSES, "us-dress-size", "6"),
        ("AU 10", "uk", ProductType.SKIRTS, "au-dress-size", "10"),
        ("UK 7", "uk", ProductType.SHOES, "uk-adult-shoe-size", "7"),
        ("EU 41", "uk", ProductType.BOOTS, "eu-adult-shoe-size", "41"),
        ("US 8", "uk", ProductType.TRAINERS, "us-adult-shoe-size", "8"),
        ("12", "eu", ProductType.DRESSES, "eu-dress-size", "12"),
        ("12", "fr", ProductType.DRESSES, "eu-dress-size", "12"),
        ("12", "us", ProductType.DRESSES, "us-dress-size", "12"),
        ("12", "au", ProductType.NIGHTWEAR, "au-dress-size", "12"),
        ("12", "uk", ProductType.SHOES, "uk-adult-shoe-size", "12"),
        ("41", "eu", ProductType.SHOES, "eu-adult-shoe-size", "41"),
        ("32", "uk", ProductType.JEANS, "uk-waist-size", "32"),
        ("32", "us", ProductType.TROUSERS, "us-waist-size", "32"),
        ("32", "eu", ProductType.JEANS, "eu-waist-size", "32"),
        ("8", "uk", ProductType.SHORTS, "uk-waist-size", "8"),
    ],
)
def test_regional_and_bare_numbers(raw, region, product, slug, value):
    decoded = decode_size_description(raw, region, product_type=product)
    assert decoded.sizes
    assert decoded.sizes[0].size_unit.slug == slug
    assert str(decoded.sizes[0].raw) == value
    assert decoded.confidence > 0


@pytest.mark.parametrize(
    ("raw", "product", "expected"),
    [
        (
            "30/32",
            ProductType.JEANS,
            [("in-waist-size", "30"), ("in-trousers-inseam", "32")],
        ),
        (
            "W30 L32",
            ProductType.TROUSERS,
            [("in-waist-size", "30"), ("in-trousers-inseam", "32")],
        ),
        (
            "30 x 32",
            ProductType.JEANS,
            [("in-waist-size", "30"), ("in-trousers-inseam", "32")],
        ),
        ("30/32", None, [("in-waist-size", "30"), ("in-trousers-inseam", "32")]),
        (
            "28S",
            ProductType.TROUSERS,
            [("in-waist-size", "28"), ("trouser-length", "short")],
        ),
        (
            "32R",
            ProductType.JEANS,
            [("in-waist-size", "32"), ("trouser-length", "regular")],
        ),
        ("30L", None, [("in-waist-size", "30"), ("trouser-length", "long")]),
    ],
)
def test_waist_compounds(raw, product, expected):
    decoded = decode_size_description(raw, "uk", product_type=product)
    assert _ids(decoded) == expected
    assert decoded.format_id in {"waist-leg", "waist-length", "unit-patterns"}


@pytest.mark.parametrize(
    ("raw", "product", "expected"),
    [
        ("32DD", ProductType.BRAS, [("uk-band-size", "32"), ("uk-cup-size", "DD")]),
        ("34E", None, [("uk-band-size", "34"), ("uk-cup-size", "E")]),
        ("36FF", ProductType.BRAS, [("uk-band-size", "36"), ("uk-cup-size", "FF")]),
        ("DD", ProductType.BRAS, [("uk-cup-size", "DD")]),
    ],
)
def test_bra_strings(raw, product, expected):
    decoded = decode_size_description(raw, "uk", product_type=product)
    assert _ids(decoded) == expected


@pytest.mark.parametrize(
    ("raw", "token", "display"),
    [
        ("5-6 years", "5-6y", "5-6 years"),
        ("5-6 yrs", "5-6y", "5-6 years"),
        ("12Y", "12y", "12 years"),
        ("12 years", "12y", "12 years"),
        ("0-3 months", "0-3m", "0-3 months"),
        ("6 mths", "6m", "6 months"),
        ("3m", "3m", "3 months"),
        ("1 month", "1m", "1 month"),
        ("1 year", "1y", "1 year"),
    ],
)
def test_age_bands(raw, token, display):
    decoded = decode_size_description(raw, "uk")
    assert decoded.sizes[0].size_unit.slug == "age"
    assert decoded.sizes[0].raw == token
    assert decoded.sizes[0].display() == display
    assert encode_size_description(decoded.sizes, "uk").text == display


@pytest.mark.parametrize(
    ("raw", "product", "slug", "token"),
    [
        ("Petite", ProductType.DRESSES, "proportion", "petite"),
        ("PT", ProductType.DRESSES, "proportion", "petite"),
        ("Extra Tall", ProductType.DRESSES, "proportion", "extra-tall"),
        ("Tall", ProductType.CASUAL_TOPS, "proportion", "tall"),
        ("10 Petite", ProductType.DRESSES, "proportion", "petite"),
        ("Regular", ProductType.TROUSERS, "trouser-length", "regular"),
        ("standard", ProductType.JEANS, "trouser-length", "regular"),
        ("Short", ProductType.TROUSERS, "trouser-length", "short"),
        ("Extra short", ProductType.TROUSERS, "trouser-length", "extra-short"),
        ("Extra long", ProductType.JEANS, "trouser-length", "extra-long"),
        ("Regular", ProductType.SHIRTS, "top-length", "regular"),
        ("Long", ProductType.KNITWEAR, "top-length", "long"),
        ("Extra short", ProductType.CASUAL_TOPS, "top-length", "extra-short"),
    ],
)
def test_proportion_and_length_words(raw, product, slug, token):
    decoded = decode_size_description(raw, "uk", product_type=product)
    matched = [size for size in decoded.sizes if size.size_unit.slug == slug]
    assert matched and matched[0].raw == token


@pytest.mark.parametrize(
    ("raw", "product", "token"),
    [
        ("G", ProductType.SHOES, "wide"),
        ("G (Wide Fit)", ProductType.SHOES, "wide"),
        ("D", ProductType.BOOTS, "narrow"),
        ("E", ProductType.SHOES, "narrow"),
        ("F", ProductType.TRAINERS, "standard"),
        ("H", ProductType.SHOES, "extra-wide"),
        ("Extra Wide", ProductType.BOOTS, "extra-wide"),
        ("Narrow", ProductType.SHOES, "narrow"),
        ("Medium", ProductType.TRAINERS, "standard"),
        ("Wide fit", ProductType.SHOES, "wide"),
        ("UK 6 Wide", ProductType.SHOES, "wide"),
    ],
)
def test_shoe_widths(raw, product, token):
    decoded = decode_size_description(raw, "uk", product_type=product)
    width = [size for size in decoded.sizes if size.size_type.slug == "shoe-width"]
    assert width and width[0].raw == token


@pytest.mark.parametrize(
    ("raw", "product", "slug", "value"),
    [
        ('32"', ProductType.JEANS, "in-waist-size", "32"),
        ("81cm", ProductType.JEANS, "cm-waist-size", "81"),
        ('15"', ProductType.DRESS_SHIRTS, "in-collar-size", "15"),
        ("38cm", ProductType.DRESS_SHIRTS, "cm-collar-size", "38"),
        ('40"', ProductType.OUTERWEAR, "in-chest-size", "40"),
    ],
)
def test_suffixed_lengths(raw, product, slug, value):
    decoded = decode_size_description(raw, "uk", product_type=product)
    assert _ids(decoded) == [(slug, value)]
    assert decoded.confidence >= 0.9


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "not-a-size", "one size", "XXL", "S", "short sleeve", "Pace Breaker"],
)
def test_unrecognised_cells(raw):
    decoded = decode_size_description(raw, "uk", product_type=ProductType.DRESSES)
    if raw.strip() == "":
        assert decoded.sizes == ()
        assert decoded.discarded == ()
    else:
        assert (
            decoded.format_id is None or decoded.sizes == () or decoded.confidence < 0.5
        )
        if not decoded.sizes:
            assert decoded.discarded[0].reason == "unrecognised"


def test_product_type_rejects_a_cross_range_compound():
    dresses = decode_size_description("30/32", "uk", product_type=ProductType.DRESSES)
    jeans = decode_size_description("30/32", "uk", product_type=ProductType.JEANS)
    assert jeans.format_id == "waist-leg"
    assert dresses.format_id != "waist-leg"


def test_ambiguous_string_lowers_confidence_and_lists_alternatives():
    decoded = decode_size_description("UK 10", "uk", product_type=ProductType.DRESSES)
    assert "regional-number" in decoded.alternatives
    assert decoded.confidence <= 0.6


def test_label_synonyms_round_trip_through_size():
    assert Size("R", TROUSER_LENGTH_SIZE).raw == "regular"
    assert Size("std", TROUSER_LENGTH_SIZE).raw == "regular"
    assert Size("extra-short", TROUSER_LENGTH_SIZE).raw == "extra-short"
    assert Size("XL", TROUSER_LENGTH_SIZE).display() == "Extra long"
    assert Size("extra long", TOP_LENGTH_SIZE).raw == "extra-long"
    assert Size("G", SHOE_WIDTH_SIZE).raw == "wide"
    assert Size("medium", SHOE_WIDTH_SIZE).raw == "standard"
    assert Size("pt", PROPORTION_SIZE).raw == "petite"
    assert Size("5-6y", AGE_SIZE).display() == "5-6 years"
    with pytest.raises(ValueError):
        Size("banana", TROUSER_LENGTH_SIZE)


def test_every_chart_unit_has_a_value_group():
    from fashion_size.types import SIZE_UNITS

    for unit in SIZE_UNITS:
        patterns = unit.recognition_patterns()
        assert patterns, unit.slug
        assert "value" in patterns[0].groupindex


@pytest.mark.parametrize(
    ("raw", "product", "slug"),
    [
        ("L32", ProductType.JEANS, "in-trousers-inseam"),
        ('L32"', ProductType.TROUSERS, "in-trousers-inseam"),
        ("L32in", ProductType.JEANS, "in-trousers-inseam"),
        ("L32 in", ProductType.JEANS, "in-trousers-inseam"),
        ("L 32", ProductType.TROUSERS, "in-trousers-inseam"),
        ('L 32"', ProductType.JEANS, "in-trousers-inseam"),
        ("L 32in", ProductType.TROUSERS, "in-trousers-inseam"),
        ("L 32 in", ProductType.JEANS, "in-trousers-inseam"),
        ("L8", ProductType.SHORTS, "in-shorts-inseam"),
        ("L 9 in", ProductType.SHORTS, "in-shorts-inseam"),
        ("L32", None, "in-trousers-inseam"),
        ("L8", None, "in-shorts-inseam"),
    ],
)
def test_inseam_accepts_l_prefix(raw, product, slug):
    for unit in (INCH_INSIDE_LEG, INCH_TROUSERS_INSEAM, INCH_SHORTS_INSEAM):
        match = unit.recognition_patterns()[0].fullmatch(raw)
        assert match is not None
        assert match.group("value") in {"32", "8", "9"}
    decoded = decode_size_description(raw, "uk", product_type=product)
    assert decoded.sizes[0].size_unit.slug == slug


@pytest.mark.parametrize(
    "raw",
    ["W30", 'W30"', "W30in", "W30 in", "W 30", 'W 30"', "W 30in", "W 30 in"],
)
def test_inch_waist_accepts_w_prefix(raw):
    match = INCH_WAIST_SIZE.recognition_patterns()[0].fullmatch(raw)
    assert match is not None
    assert match.group("value") == "30"
    decoded = decode_size_description(raw, "uk", product_type=ProductType.JEANS)
    assert _ids(decoded)[0] == ("in-waist-size", "30")


@pytest.mark.parametrize(
    ("unit", "sample"),
    [
        (UK_DRESS_SIZE, "UK 14"),
        (US_DRESS_SIZE, "US 8"),
        (EU_DRESS_SIZE, "EUR 40"),
        (UK_ADULT_SHOE_SIZE, "UK 5.5"),
        (EU_ADULT_SHOE_SIZE, "EU 38"),
        (UK_CUP_SIZE, "DD"),
        (UK_BAND_SIZE, "UK 34"),
        (INCH_WAIST_SIZE, '28"'),
        (CM_WAIST_SIZE, "72cm"),
        (INCH_COLLAR_SIZE, "16.5 in"),
        (TROUSER_LENGTH_SIZE, "Regular"),
        (SHOE_WIDTH_SIZE, "extra wide"),
        (PROPORTION_SIZE, "Petite"),
        (AGE_SIZE, "9-12 months"),
    ],
)
def test_unit_pattern_extracts_the_sample(unit, sample):
    match = next(
        (
            found
            for pattern in unit.recognition_patterns()
            if (found := pattern.search(sample)) is not None
        ),
        None,
    )
    assert match is not None
    assert match.group("value")


def test_encode_length_follows_preferred_region_unit():
    inches = Size(30, INCH_WAIST_SIZE)
    as_eu = encode_size_description(
        [inches], "uk", preferred_regions=("eu",), product_type=ProductType.JEANS
    )
    assert as_eu.used[0].size_unit.length_unit == "cm"
    assert "cm" in as_eu.text

    centimetres = Size(76.2, CM_WAIST_SIZE)
    as_uk = encode_size_description([centimetres], "eu", preferred_regions=("uk",))
    assert as_uk.used[0].size_unit.length_unit == "in"


def test_encode_keeps_chart_size_when_preferred_region_is_absent():
    only_us = encode_size_description(
        [Size(6, US_DRESS_SIZE)],
        "uk",
        preferred_regions=("uk", "eu"),
        product_type=ProductType.DRESSES,
    )
    assert only_us.text == "US 6"
    assert only_us.discarded == ()


def test_encode_discards_duplicate_regions_and_unused_parts():
    encoded = encode_size_description(
        [
            Size(10, UK_DRESS_SIZE),
            Size(38, EU_DRESS_SIZE),
            Size("petite", PROPORTION_SIZE),
        ],
        "uk",
        preferred_regions=("uk", "eu"),
        product_type=ProductType.DRESSES,
        format="regional-number",
    )
    assert encoded.text == "UK 10"
    assert encoded.confidence == 1.0
    reasons = {item.reason for item in encoded.discarded}
    assert "duplicate" in reasons
    assert "unused" in reasons


def test_encode_named_formats():
    bra = encode_size_description(
        [Size(34, UK_BAND_SIZE), Size("E", UK_CUP_SIZE)],
        "uk",
        format="bra",
    )
    assert bra.text == "34E"
    assert bra.format_id == "bra"

    shoe = encode_size_description(
        [Size(6, UK_ADULT_SHOE_SIZE), Size("wide", SHOE_WIDTH_SIZE)],
        "uk",
        product_type=ProductType.SHOES,
    )
    assert shoe.format_id == "shoe"
    assert shoe.text == "UK 6 Wide"

    age = encode_size_description([Size("0-3 months", AGE_SIZE)], "uk")
    assert age.text == "0-3 months"
    assert age.format_id == "age"


@pytest.mark.parametrize(
    ("region", "expected"),
    [
        ("uk", "Short"),
        ("us", "Short"),
        ("fr", "Court"),
        ("eu", "Short"),
    ],
)
def test_encode_translates_length_words(region, expected):
    encoded = encode_size_description(
        [Size("short", TROUSER_LENGTH_SIZE)],
        region,
        preferred_regions=(region,),
        product_type=ProductType.TROUSERS,
    )
    assert encoded.text == expected


def test_encode_empty_and_unknown_format():
    empty = encode_size_description([], "uk")
    assert empty.text == ""
    assert empty.confidence == 0.0
    with pytest.raises(ValueError, match="Unknown size description format"):
        encode_size_description([Size(10, UK_DRESS_SIZE)], "uk", format="nope")
    with pytest.raises(ValueError, match="source_region"):
        decode_size_description("10", "universal")
    with pytest.raises(ValueError, match="preferred_regions"):
        encode_size_description(
            [Size(10, UK_DRESS_SIZE)], "uk", preferred_regions=("universal",)
        )


def test_source_region_accepts_locale_enum():
    from fashion_size.types import Locale

    decoded = decode_size_description(
        "UK 8", Locale.US, product_type=ProductType.DRESSES
    )
    assert decoded.sizes[0].size_unit.slug == "uk-dress-size"


def test_whitespace_is_collapsed_before_matching():
    decoded = decode_size_description(
        "  UK   10  ", "uk", product_type=ProductType.DRESSES
    )
    assert decoded.sizes[0].raw == 10


def test_jeans_slash_round_trips():
    decoded = decode_size_description("W32 / L30", "uk", product_type=ProductType.JEANS)
    assert _ids(decoded) == [
        ("in-waist-size", "32"),
        ("in-trousers-inseam", "30"),
    ]
    assert encode_size_description(decoded.sizes, "uk").text == "32/30"
