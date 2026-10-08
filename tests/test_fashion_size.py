"""Behaviour covered by the README and the charts shipped in the package."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

import fashion_size.charts as charts
from fashion_size import (
    PRODUCT_TYPES,
    SUPPORTED_BRANDS,
    ConversionSourceKind,
    DefaultChartReason,
    Demographic,
    ProductType,
    __version__,
    register_display_language,
)
from fashion_size.brands import BRANDS, BrandName
from fashion_size.charts import (
    BrandConversionChart,
    _parse_rows,
    _read_chart_file,
    _validate_override,
    chart_for,
    charts_for_brand,
    load_brand_charts,
)
from fashion_size.product_types import PRODUCT_TYPE_SLUGS, resolve_product_type
from fashion_size.size_types import SizeTypeSlug
from fashion_size.types import (
    CM_CHEST_SIZE,
    EU_ADULT_SHOE_SIZE,
    EU_BAND_SIZE,
    EU_CUP_SIZE,
    EU_DRESS_SIZE,
    FR_BAND_SIZE,
    INCH_CHEST_SIZE,
    UK_ADULT_SHOE_SIZE,
    UK_BABY_SHOE_SIZE,
    UK_BAND_SIZE,
    UK_CHEST_SIZE,
    UK_CUP_SIZE,
    UK_DRESS_SIZE,
    UK_KIDS_SHOE_SIZE,
    UK_WAIST_SIZE,
    US_CUP_SIZE,
    IncompatibleSizeError,
    LengthOutOfRangeError,
    MissingScaleError,
    Size,
    UnknownSizeError,
    parse_size_unit_slug,
    size_from_attribute_option,
    size_unit_choices_for_type,
)


def test_version_is_the_current_release():
    assert __version__ == "2026.10.8"


def test_readme_brand_chart_example():
    assert "Dune London" in SUPPORTED_BRANDS
    chart = chart_for(
        "Dune London", "adult-shoe", "adult", "female", product_type=ProductType.SHOES
    )
    assert chart is not None
    assert chart.updated_at == datetime(2026, 3, 29, tzinfo=UTC)
    assert chart.source_url == "https://www.dunelondon.com/size-guide"
    assert chart.source_notes == ""
    mens = chart_for(
        "Dune London", "adult-shoe", "adult", "male", product_type=ProductType.SHOES
    )
    assert mens is not None
    assert "AU values match US" in mens.source_notes
    assert {"uk": 7, "eu": 40, "us": 9, "au": 9} in chart.rows
    assert chart.covers(ProductType.SHOES)
    assert not chart.covers(ProductType.JEANS)


def test_readme_dress_conversion():
    value = Size.from_raw("10", UK_DRESS_SIZE)
    converted = value.convert_to_locale("eu", demographic=Demographic("adult", "female"))
    assert converted.size == Size.from_raw(38, EU_DRESS_SIZE)
    assert converted.source.kind == ConversionSourceKind.DEFAULT
    assert converted.source.default_reason == DefaultChartReason.NO_BRAND
    direct = value.convert(EU_DRESS_SIZE, demographic=Demographic("adult", "female"))
    assert direct.size == converted.size
    assert direct.source.kind == converted.source.kind
    assert str(converted) == "EU 38"
    assert str(value) == "UK 10"


def test_locale_charts():
    women_10 = Size.from_raw("10", UK_DRESS_SIZE)
    assert women_10.convert_to_locale("us", demographic=Demographic("adult", "female")).raw == 6
    assert women_10.convert_to_locale("au", demographic=Demographic("adult", "female")).raw == 10
    french = women_10.convert_to_locale("fr", demographic=Demographic("adult", "female"))
    assert french.size_unit is EU_DRESS_SIZE
    assert french.raw == 38
    assert str(french) == "EU 38"

    assert (
        Size.from_raw(38, UK_DRESS_SIZE)
        .convert_to_locale("eu", demographic=Demographic("adult", "male"))
        .raw
        == 48
    )
    assert (
        Size.from_raw(38, UK_DRESS_SIZE)
        .convert_to_locale("eu", demographic=Demographic("adult", "unisex"))
        .raw
        == 48
    )
    assert (
        Size.from_raw(8, UK_DRESS_SIZE)
        .convert_to_locale("eu", demographic=Demographic("child", "female"))
        .raw
        == 128
    )

    women_shoe = Size.from_raw(7, UK_ADULT_SHOE_SIZE)
    assert women_shoe.convert_to_locale("eu", demographic=Demographic("adult", "female")).raw == 41
    assert women_shoe.convert_to_locale("us", demographic=Demographic("adult", "female")).raw == 9
    assert women_shoe.convert_to_locale("au", demographic=Demographic("adult", "female")).raw == 9
    half = Size.from_raw("7.5", UK_ADULT_SHOE_SIZE).convert_to_locale(
        "eu", demographic=Demographic("adult", "female")
    )
    assert half.raw == Decimal("41.5")
    assert str(half) == "EU 41.5"

    men_shoe = Size.from_raw(7, UK_ADULT_SHOE_SIZE)
    assert men_shoe.convert_to_locale("us", demographic=Demographic("adult", "male")).raw == 8
    assert men_shoe.convert_to_locale("au", demographic=Demographic("adult", "unisex")).raw == 7
    men_half = Size.from_raw("12.5", UK_ADULT_SHOE_SIZE)
    assert men_half.convert_to_locale("eu", demographic=Demographic("adult", "male")).raw == Decimal("47.5")
    assert men_half.convert_to_locale("us", demographic=Demographic("adult", "male")).raw == Decimal("13.5")
    assert men_half.convert_to_locale("au", demographic=Demographic("adult", "male")).raw == Decimal("12.5")
    assert (
        Size.from_raw(6, UK_KIDS_SHOE_SIZE)
        .convert_to_locale("eu", demographic=Demographic("child", "male"))
        .raw
        == 23
    )
    assert (
        Size.from_raw(0, UK_BABY_SHOE_SIZE)
        .convert_to_locale("eu", demographic=Demographic("baby", "unisex"))
        .raw
        == 16
    )

    band = Size.from_raw(34, UK_BAND_SIZE)
    assert band.convert_to_locale("eu", demographic=Demographic("adult", "female")).size == Size.from_raw(
        75, EU_BAND_SIZE
    )
    assert band.convert_to_locale("au", demographic=Demographic("adult", "male")).raw == 12
    assert band.convert_to_locale("fr", demographic=Demographic("adult", "female")).size == Size.from_raw(
        90, FR_BAND_SIZE
    )
    assert (
        Size.from_raw(90, FR_BAND_SIZE)
        .convert_to_locale("uk", demographic=Demographic("adult", "female"))
        .raw
        == 34
    )

    assert (
        Size.from_raw(32, UK_WAIST_SIZE)
        .convert_to_locale("eu", demographic=Demographic("adult", "male"))
        .raw
        == 48
    )
    assert (
        Size.from_raw(40, UK_CHEST_SIZE)
        .convert_to_locale("eu", demographic=Demographic("adult", "male"))
        .raw
        == 50
    )
    assert (
        Size.from_raw(22, UK_WAIST_SIZE)
        .convert_to_locale("eu", demographic=Demographic("child", "male"))
        .raw
        == 56
    )

    cup = Size.from_raw("dd", UK_CUP_SIZE)
    assert str(cup) == "DD"
    assert cup.convert_to_locale("eu", demographic=Demographic("adult", "female")).raw == "E"
    assert (
        Size.from_raw("E", UK_CUP_SIZE)
        .convert_to_locale("us", demographic=Demographic("adult", "female"))
        .raw
        == "DDD"
    )


def test_cup_alpha_tokens_convert_with_identity_across_locales():
    women = Demographic("adult", "female")
    alpha = Size.from_raw("small", UK_CUP_SIZE)
    assert alpha.raw == "Small"
    assert str(alpha) == "Small"
    converted = alpha.convert_to_locale("eu", demographic=women)
    assert converted.raw == "Small"
    assert converted.source.kind == ConversionSourceKind.IDENTITY
    assert (
        Size.from_raw("XL", US_CUP_SIZE)
        .convert_to_locale("uk", demographic=women)
        .raw
        == "XL"
    )
    assert Size.from_raw("med", UK_CUP_SIZE).raw == "Medium"
    assert Size.from_raw("lg", UK_CUP_SIZE).raw == "Large"
    assert (
        Size.from_raw("HH", UK_CUP_SIZE)
        .convert_to_locale("eu", demographic=women)
        .raw
        == "L"
    )
    assert (
        Size.from_raw("M", EU_CUP_SIZE)
        .convert_to_locale("us", demographic=women)
        .raw
        == "M"
    )


def test_length_conversion_and_display():
    inches = Size.from_raw(32, INCH_CHEST_SIZE)
    centimetres = inches.convert("cm", demographic=Demographic("adult", "unisex"))
    assert centimetres.size_unit is CM_CHEST_SIZE
    assert centimetres.raw == Decimal("81.28")
    assert centimetres.source.kind == ConversionSourceKind.LENGTH_FORMULA
    assert centimetres.localised_display("en-gb") == "81cm"
    assert centimetres.localised_display("de") == "81 cm"
    assert inches.localised_display("en-us") == '32"'
    assert inches.localised_display("fr") == "32 in"
    assert (
        Size.from_raw(centimetres.raw, centimetres.size_unit)
        .convert("in", demographic=Demographic("adult", "unisex"))
        .raw
        == Decimal("32")
    )

    assert (
        Size.from_raw(5, INCH_CHEST_SIZE)
        .convert("cm", demographic=Demographic("adult", "unisex"))
        .raw
        == Decimal("12.7")
    )
    assert (
        Size.from_raw(150, INCH_CHEST_SIZE)
        .convert("cm", demographic=Demographic("adult", "unisex"))
        .raw
        == Decimal("381")
    )
    assert (
        Size.from_raw(Decimal("10.3"), INCH_CHEST_SIZE).localised_display() == '10.5"'
    )
    assert (
        Size.from_raw(Decimal("10.5"), CM_CHEST_SIZE).localised_display("de") == "11 cm"
    )

    register_display_language(lambda: "de")
    assert str(inches) == "32 in"
    assert inches.localised_display("en-gb") == '32"'


def test_conversion_rejects_unknown_or_incompatible_values():
    with pytest.raises(UnknownSizeError):
        Size.from_raw(11, UK_DRESS_SIZE).convert_to_locale(
            "eu", demographic=Demographic("adult", "female")
        )
    with pytest.raises(UnknownSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_locale("eu", demographic=Demographic("adult", "male"))
    with pytest.raises(TypeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_locale("eu")  # type: ignore[call-arg]
    with pytest.raises(MissingScaleError):
        Size.from_raw(62, UK_DRESS_SIZE).convert_to_locale(
            "eu", demographic=Demographic("baby", "unisex")
        )
    with pytest.raises(ValueError, match="French|locale 'fr'|No Waist size"):
        Size.from_raw(32, UK_WAIST_SIZE).convert_to_locale("fr", demographic=Demographic("adult", "male"))
    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert(
            EU_ADULT_SHOE_SIZE, demographic=Demographic("adult", "female")
        )
    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(32, INCH_CHEST_SIZE).convert_to_locale(
            "eu", demographic=Demographic("adult", "unisex")
        )
    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert(
            "cm", demographic=Demographic("adult", "female")
        )
    with pytest.raises(LengthOutOfRangeError):
        Size.from_raw(Decimal("4.9"), INCH_CHEST_SIZE).convert(
            "cm", demographic=Demographic("adult", "unisex")
        )
    with pytest.raises(LengthOutOfRangeError):
        Size.from_raw(Decimal("12.69"), CM_CHEST_SIZE).convert(
            "in", demographic=Demographic("adult", "unisex")
        )
    with pytest.raises(LengthOutOfRangeError):
        Size.from_raw(Decimal("150.1"), INCH_CHEST_SIZE).convert(
            "cm", demographic=Demographic("adult", "unisex")
        )
    with pytest.raises(ValueError, match="cup"):
        Size.from_raw("D-E", UK_CUP_SIZE)

    same = Size.from_raw(10, UK_DRESS_SIZE)
    unchanged = same.convert(
        UK_DRESS_SIZE, demographic=Demographic("adult", "female")
    )
    assert unchanged.size is same
    assert unchanged.source.kind == ConversionSourceKind.IDENTITY
    with pytest.raises(AttributeError):
        unchanged.convert_to_locale("eu")  # type: ignore[attr-defined]


def test_band_size_uses_the_default_chart():
    converted = Size.from_raw(34, UK_BAND_SIZE).convert_to_locale(
        "eu",
        demographic=Demographic("adult", "female"),
        brand_name="Dune London",
        product_type=ProductType.SHOES,
    )
    assert converted.raw == 75
    assert converted.source.kind == ConversionSourceKind.DEFAULT
    assert converted.source.default_reason == DefaultChartReason.SIZE_TYPE_USES_DEFAULT


def test_attribute_options_and_size_unit_slugs():
    dress = size_from_attribute_option("uk-dress-size", "UK 10")
    assert dress is not None and dress.raw == 10 and dress.size_unit is UK_DRESS_SIZE
    prefixed = size_from_attribute_option(
        "uk-dress-size", "Size 10", raw_value_prefix="Size "
    )
    assert prefixed is not None and prefixed.raw == 10
    chest = size_from_attribute_option("in-chest-size", '32"')
    assert chest is not None and chest.raw == 32 and chest.size_unit is INCH_CHEST_SIZE
    cup = size_from_attribute_option("uk-cup-size", "dd")
    assert cup is not None and cup.raw == "DD"
    alpha_cup = size_from_attribute_option("uk-cup-size", "x-large")
    assert alpha_cup is not None and alpha_cup.raw == "XL"
    assert size_from_attribute_option("uk-dress-size", "small") is None
    assert size_from_attribute_option("not-a-size", "10") is None

    assert parse_size_unit_slug("fr-dress-size") is EU_DRESS_SIZE
    assert parse_size_unit_slug("fr-band-size") is FR_BAND_SIZE
    assert FR_BAND_SIZE is not EU_BAND_SIZE
    with pytest.raises(ValueError, match="Unknown size unit"):
        parse_size_unit_slug("xx-dress-size")
    assert "uk-dress-size" in dict(size_unit_choices_for_type("dress"))
    assert "uk-adult-shoe-size" not in dict(size_unit_choices_for_type("dress"))


def test_brand_name_selects_the_shipped_chart():
    adult_female = Demographic("adult", "female")
    shoe = Size.from_raw(7, UK_ADULT_SHOE_SIZE)
    default = shoe.convert_to_locale("eu", demographic=adult_female)
    dune = shoe.convert_to_locale(
        "eu",
        demographic=adult_female,
        brand_name="  dune LONDON ",
        product_type=ProductType.SHOES,
    )
    assert default.raw == 41
    assert default.source.kind == ConversionSourceKind.DEFAULT
    assert default.source.default_reason == DefaultChartReason.NO_BRAND
    assert dune.raw == 40
    assert dune.source.kind == ConversionSourceKind.BRAND
    assert dune.source.brand_chart is not None
    assert dune.source.brand_chart.brand_name == BrandName.DUNE_LONDON

    anthropologie = shoe.convert_to_locale(
        "eu",
        demographic=adult_female,
        brand_name="Anthropologie",
        product_type="shoes",
    )
    assert anthropologie.raw == default.raw
    assert anthropologie.source.default_reason == DefaultChartReason.BRAND_USES_DEFAULT

    outfitters = Size.from_raw(16, UK_DRESS_SIZE)
    dresses = outfitters.convert_to_locale(
        "us",
        demographic=adult_female,
        brand_name="Urban Outfitters",
        product_type=ProductType.DRESSES,
    )
    jeans = outfitters.convert_to_locale(
        "us",
        demographic=adult_female,
        brand_name="Urban Outfitters",
        product_type=ProductType.JEANS,
    )
    assert dresses.raw == 16
    assert dresses.source.kind == ConversionSourceKind.BRAND
    assert jeans.raw == 12
    assert jeans.source.kind == ConversionSourceKind.DEFAULT
    assert jeans.source.default_reason == DefaultChartReason.NO_MATCHING_CHART

    unknown = shoe.convert_to_locale(
        "eu",
        demographic=adult_female,
        brand_name="Not a brand",
        product_type=ProductType.SHOES,
    )
    assert unknown.raw == default.raw
    assert unknown.source.kind == ConversionSourceKind.DEFAULT
    assert unknown.source.default_reason == DefaultChartReason.UNKNOWN_BRAND
    with pytest.raises(ValueError, match="Unknown brand"):
        shoe.convert_to_locale(
            "eu",
            demographic=adult_female,
            brand_name="Not a brand",
            product_type=ProductType.SHOES,
            strict_brand_name=True,
        )
    with pytest.raises(ValueError, match="Unknown product type"):
        shoe.convert_to_locale(
            "eu",
            demographic=adult_female,
            brand_name="Dune London",
            product_type="not-a-family",
        )
    with pytest.raises(ValueError, match="brand name"):
        shoe.convert_to_locale(
            "eu",
            demographic=adult_female,
            product_type=ProductType.SHOES,
        )


def test_shipped_brand_charts_are_complete():
    charts = load_brand_charts()
    assert charts
    assert {chart.brand_name for chart in charts} <= set(SUPPORTED_BRANDS)
    assert charts_for_brand("finisterre") == ()
    assert charts_for_brand("  dune LONDON ")[0].brand_name == "Dune London"

    for chart in charts:
        assert chart.size_type in SizeTypeSlug
        assert chart.updated_at.tzinfo is not None
        assert chart.source_url.startswith("https://")
        assert chart.rows
        product_type = chart.product_types[0] if chart.product_types else None
        gender = chart.gender or "female"
        found = chart_for(
            chart.brand_name,
            chart.size_type,
            chart.age_group,
            gender,
            product_type=product_type,
        )
        assert found is chart

    kids = chart_for(
        "Salt-Water Sandals",
        "kids-shoe",
        "child",
        "male",
        product_type=ProductType.SHOES,
    )
    assert kids is not None and kids.gender == ""
    assert {"uk": 12.5, "eu": 31, "us": 13.5, "au": 12.5} in kids.rows
    mallet = chart_for(
        "Mallet",
        "adult-shoe",
        "adult",
        "male",
        product_type=ProductType.SHOES,
    )
    assert mallet is not None
    assert {"uk": 12.5, "eu": 46.5, "us": 13.5, "au": 12.5} in mallet.rows
    jeans = chart_for(
        "Urban Outfitters", "dress", "adult", "female", product_type=ProductType.JEANS
    )
    assert jeans is None
    dresses = chart_for(
        "Urban Outfitters", "dress", "adult", " Female ", product_type="dresses"
    )
    assert dresses is not None and dresses.covers("dresses")
    assert dresses.covers(ProductType.SUITS)
    assert dresses.covers("suit-jackets")


@pytest.mark.parametrize(
    ("product_type", "slug", "label"),
    [
        (ProductType.SWIMWEAR, "swimwear", "Swimwear"),
        (ProductType.OUTERWEAR, "outerwear", "Outerwear"),
        (ProductType.CASUAL_BOTTOMS, "casual-bottoms", "Casual Bottoms"),
        (ProductType.NIGHTWEAR, "nightwear", "Nightwear"),
        (ProductType.BRAS, "bras", "Bras"),
        (ProductType.SKIRTS, "skirts", "Skirts"),
        (ProductType.SHORTS, "shorts", "Shorts"),
        (ProductType.HOSIERY, "hosiery", "Hosiery"),
        (ProductType.SUITS, "suits", "Suits & Tailoring"),
    ],
)
def test_named_product_types(product_type, slug, label):
    assert product_type == slug
    assert product_type.label == label
    assert product_type in PRODUCT_TYPES
    assert resolve_product_type(f" {slug} ") is product_type


def test_suit_jackets_resolves_to_suits():
    assert not hasattr(ProductType, "SUIT_JACKETS")
    assert "suit-jackets" not in PRODUCT_TYPE_SLUGS
    assert resolve_product_type("suit-jackets") is ProductType.SUITS


def test_chart_with_no_product_types_covers_every_product_type():
    chart = BrandConversionChart(
        brand_name=BrandName.ANTHROPOLOGIE,
        size_type="dress",
        age_group="adult",
        gender="female",
        product_types=(),
        updated_at=datetime(2026, 3, 29, tzinfo=UTC),
        source_url="",
        source_notes="",
        rows=({"uk": 10, "eu": 38, "us": 6, "au": 10},),
    )
    assert chart.covers("jeans")
    assert chart.covers("shoes")
    assert chart.covers(ProductType.SWIMWEAR)
    assert chart.covers(ProductType.OUTERWEAR)
    assert chart.covers(ProductType.CASUAL_BOTTOMS)
    assert chart.covers(ProductType.NIGHTWEAR)
    assert chart.covers(ProductType.BRAS)
    assert chart.covers(ProductType.SKIRTS)
    assert chart.covers(ProductType.SHORTS)
    assert chart.covers(ProductType.HOSIERY)


def _sample_override():
    return next(chart for brand in BRANDS for chart in brand.charts)


@pytest.mark.parametrize(
    ("rows", "match"),
    [
        ([], "no rows"),
        ([{"uk": 7, "eu": 40}], "uk, eu, us, and au"),
        ([{"uk": True, "eu": 40, "us": 9, "au": 9}], "invalid"),
    ],
)
def test_chart_rows_are_rejected_when_incomplete(rows, match):
    with pytest.raises(ValueError, match=match):
        _parse_rows("example", rows)


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"size_type": "hat"}, "size type"),
        ({"age_group": "teen"}, "age group"),
        ({"gender": "unisex"}, "gender"),
        ({"product_types": ("not-a-family",)}, "product types"),
        ({"id": "not-a-uuid"}, "not a UUID"),
        ({"updated_at": datetime(2026, 3, 29)}, "timezone"),
    ],
)
def test_override_metadata_is_rejected_when_incomplete(changes, match):
    with pytest.raises(ValueError, match=match):
        _validate_override("Example", replace(_sample_override(), **changes))


def test_override_files_match_the_catalog():
    directory = Path(charts.__file__).resolve().parent / "fixtures" / "charts"
    ids = [chart.id for brand in BRANDS for chart in brand.charts]
    assert ids
    assert len(ids) == len(set(ids))
    assert {path.stem for path in directory.glob("*.json")} == set(ids)
    assert tuple(brand.name for brand in BRANDS) == SUPPORTED_BRANDS
    assert set(BrandName) == set(SUPPORTED_BRANDS)
    anthropologie = next(brand for brand in BRANDS if brand.name == "Anthropologie")
    dune = next(brand for brand in BRANDS if brand.name == "Dune London")
    assert not anthropologie.differs_from_default
    assert dune.differs_from_default
    assert charts_for_brand("Anthropologie") == ()
    assert any(chart.brand_name == "Dune London" for chart in load_brand_charts())


def test_chart_file_requires_source_and_rows(tmp_path: Path):
    path = tmp_path / f"{_sample_override().id}.json"
    rows = [{"uk": 7, "eu": 40, "us": 9, "au": 9}]
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "source_url": "https://example.com/sizes",
                "source_notes": "",
                "rows": rows,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="schema"):
        _read_chart_file(path)
    path.write_text(
        json.dumps({"schema_version": 1, "rows": rows}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source_url"):
        _read_chart_file(path)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_url": "  ",
                "source_notes": "",
                "rows": rows,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source_url"):
        _read_chart_file(path)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_url": "https://example.com/sizes",
                "source_notes": None,
                "rows": rows,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source_notes"):
        _read_chart_file(path)
