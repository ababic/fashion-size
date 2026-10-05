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
    SUPPORTED_BRANDS,
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
from fashion_size.size_types import SizeTypeSlug
from fashion_size.types import (
    ADULT_SHOE,
    BAND_SIZE,
    CM_CHEST_SIZE,
    EU_ADULT_SHOE_SIZE,
    EU_BAND_SIZE,
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
    ConversionScale,
    IncompatibleSizeError,
    LengthFormula,
    LengthOutOfRangeError,
    LocaleSizeRow,
    MissingScaleError,
    Size,
    UnknownSizeError,
    parse_size_unit_slug,
    size_from_attribute_option,
    size_unit_choices_for_type,
)


def test_version_is_the_initial_release():
    assert __version__ == "0.1.0"


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
    converted = value.convert_to_locale("eu", age_group="adult", gender="female")
    assert converted.size == Size.from_raw(38, EU_DRESS_SIZE)
    assert isinstance(converted.chart, ConversionScale)
    assert str(converted) == "EU 38"
    assert str(value) == "UK 10"


def test_locale_charts():
    women_10 = Size.from_raw("10", UK_DRESS_SIZE)
    assert women_10.convert_to_locale("us", age_group="adult", gender="female").raw == 6
    assert women_10.convert_to_locale("au", age_group="adult", gender="female").raw == 10
    french = women_10.convert_to_locale("fr", age_group="adult", gender="female")
    assert french.size_unit is EU_DRESS_SIZE
    assert french.raw == 38
    assert str(french) == "EU 38"

    assert (
        Size.from_raw(38, UK_DRESS_SIZE)
        .convert_to_locale("eu", age_group="adult", gender="male")
        .raw
        == 48
    )
    assert (
        Size.from_raw(38, UK_DRESS_SIZE)
        .convert_to_locale("eu", age_group="adult", gender="unisex")
        .raw
        == 48
    )
    assert (
        Size.from_raw(8, UK_DRESS_SIZE)
        .convert_to_locale("eu", age_group="child", gender="female")
        .raw
        == 128
    )

    women_shoe = Size.from_raw(7, UK_ADULT_SHOE_SIZE)
    assert women_shoe.convert_to_locale("eu", age_group="adult", gender="female").raw == 41
    assert women_shoe.convert_to_locale("us", age_group="adult", gender="female").raw == 9
    assert women_shoe.convert_to_locale("au", age_group="adult", gender="female").raw == 9
    half = Size.from_raw("7.5", UK_ADULT_SHOE_SIZE).convert_to_locale(
        "eu", age_group="adult", gender="female"
    )
    assert half.raw == Decimal("41.5")
    assert str(half) == "EU 41.5"

    men_shoe = Size.from_raw(7, UK_ADULT_SHOE_SIZE)
    assert men_shoe.convert_to_locale("us", age_group="adult", gender="male").raw == 8
    assert men_shoe.convert_to_locale("au", age_group="adult", gender="unisex").raw == 7
    men_half = Size.from_raw("12.5", UK_ADULT_SHOE_SIZE)
    assert men_half.convert_to_locale("eu", age_group="adult", gender="male").raw == Decimal("47.5")
    assert men_half.convert_to_locale("us", age_group="adult", gender="male").raw == Decimal("13.5")
    assert men_half.convert_to_locale("au", age_group="adult", gender="male").raw == Decimal("12.5")
    assert (
        Size.from_raw(6, UK_KIDS_SHOE_SIZE)
        .convert_to_locale("eu", age_group="child", gender="male")
        .raw
        == 23
    )
    assert (
        Size.from_raw(0, UK_BABY_SHOE_SIZE)
        .convert_to_locale("eu", age_group="baby", gender="unisex")
        .raw
        == 16
    )

    band = Size.from_raw(34, UK_BAND_SIZE)
    assert band.convert_to_locale("eu", age_group="adult", gender="female").size == Size.from_raw(
        75, EU_BAND_SIZE
    )
    assert band.convert_to_locale("au", age_group="adult", gender="male").raw == 12
    assert band.convert_to_locale("fr", age_group="adult", gender="female").size == Size.from_raw(
        90, FR_BAND_SIZE
    )
    assert (
        Size.from_raw(90, FR_BAND_SIZE)
        .convert_to_locale("uk", age_group="adult", gender="female")
        .raw
        == 34
    )

    assert (
        Size.from_raw(32, UK_WAIST_SIZE)
        .convert_to_locale("eu", age_group="adult", gender="male")
        .raw
        == 48
    )
    assert (
        Size.from_raw(40, UK_CHEST_SIZE)
        .convert_to_locale("eu", age_group="adult", gender="male")
        .raw
        == 50
    )
    assert (
        Size.from_raw(22, UK_WAIST_SIZE)
        .convert_to_locale("eu", age_group="child", gender="male")
        .raw
        == 56
    )

    cup = Size.from_raw("dd", UK_CUP_SIZE)
    assert str(cup) == "DD"
    assert cup.convert_to_locale("eu", age_group="adult", gender="female").raw == "E"
    assert (
        Size.from_raw("E", UK_CUP_SIZE)
        .convert_to_locale("us", age_group="adult", gender="female")
        .raw
        == "DDD"
    )


def test_length_conversion_and_display():
    inches = Size.from_raw(32, INCH_CHEST_SIZE)
    centimetres = inches.convert_to_unit("cm")
    assert centimetres.size_unit is CM_CHEST_SIZE
    assert centimetres.raw == Decimal("81.28")
    assert isinstance(centimetres.chart, LengthFormula)
    assert centimetres.localised_display("en-gb") == "81cm"
    assert centimetres.localised_display("de") == "81 cm"
    assert inches.localised_display("en-us") == '32"'
    assert inches.localised_display("fr") == "32 in"
    assert (
        Size.from_raw(centimetres.raw, centimetres.size_unit).convert_to_unit("in").raw
        == Decimal("32")
    )

    assert Size.from_raw(5, INCH_CHEST_SIZE).convert_to_unit("cm").raw == Decimal("12.7")
    assert Size.from_raw(150, INCH_CHEST_SIZE).convert_to_unit("cm").raw == Decimal("381")
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
            "eu", age_group="adult", gender="female"
        )
    with pytest.raises(UnknownSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_locale("eu", age_group="adult", gender="male")
    with pytest.raises(MissingScaleError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_locale("eu")
    with pytest.raises(MissingScaleError):
        Size.from_raw(62, UK_DRESS_SIZE).convert_to_locale(
            "eu", age_group="baby", gender="unisex"
        )
    with pytest.raises(ValueError, match="French|locale 'fr'|No Waist size"):
        Size.from_raw(32, UK_WAIST_SIZE).convert_to_locale("fr", age_group="adult", gender="male")
    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_locale(
            EU_ADULT_SHOE_SIZE, age_group="adult", gender="female"
        )
    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(32, INCH_CHEST_SIZE).convert_to_locale("eu")
    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_unit("cm")
    with pytest.raises(LengthOutOfRangeError):
        Size.from_raw(Decimal("4.9"), INCH_CHEST_SIZE).convert_to_unit("cm")
    with pytest.raises(LengthOutOfRangeError):
        Size.from_raw(Decimal("12.69"), CM_CHEST_SIZE).convert_to_unit("in")
    with pytest.raises(LengthOutOfRangeError):
        Size.from_raw(Decimal("150.1"), INCH_CHEST_SIZE).convert_to_unit("cm")
    with pytest.raises(ValueError, match="cup"):
        Size.from_raw("D-E", UK_CUP_SIZE)

    same = Size.from_raw(10, UK_DRESS_SIZE)
    unchanged = same.convert_to_locale(UK_DRESS_SIZE)
    assert unchanged.size is same
    assert unchanged.chart is None
    with pytest.raises(AttributeError):
        unchanged.convert_to_locale("eu")  # type: ignore[attr-defined]


def test_brand_scale_replaces_the_default_chart_when_the_size_type_allows_it():
    dune = ConversionScale(
        size_type=ADULT_SHOE,
        age_group="adult",
        gender="female",
        rows=(LocaleSizeRow.from_numbers(7, 40, 9, 9),),
    )
    converted = Size.from_raw(7, UK_ADULT_SHOE_SIZE).convert_to_locale(
        "eu",
        age_group="adult",
        gender="female",
        brand_scale=dune,
    )
    assert converted.raw == 40
    assert converted.chart is dune

    ignored = ConversionScale(
        size_type=BAND_SIZE,
        age_group="adult",
        gender="female",
        rows=(LocaleSizeRow.from_numbers(34, 1, 1, 1),),
    )
    assert (
        Size.from_raw(34, UK_BAND_SIZE)
        .convert_to_locale(
            "eu",
            age_group="adult",
            gender="female",
            brand_scale=ignored,
        )
        .raw
        == 75
    )

    with pytest.raises(IncompatibleSizeError):
        Size.from_raw(10, UK_DRESS_SIZE).convert_to_locale(
            "eu", age_group="adult", gender="female", brand_scale=dune
        )
    with pytest.raises(ValueError, match="both"):
        Size.from_raw(7, UK_ADULT_SHOE_SIZE).convert_to_locale(
            "eu", age_group="adult", brand_scale=dune
        )


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
    shoe = Size.from_raw(7, UK_ADULT_SHOE_SIZE)
    default = shoe.convert_to_locale("eu", age_group="adult", gender="female")
    dune = shoe.convert_to_locale(
        "eu",
        age_group="adult",
        gender="female",
        brand="  dune LONDON ",
        product_type=ProductType.SHOES,
    )
    assert default.raw == 41
    assert isinstance(default.chart, ConversionScale)
    assert dune.raw == 40
    assert isinstance(dune.chart, BrandConversionChart)
    assert dune.chart.brand_name == "Dune London"

    anthropologie = shoe.convert_to_locale(
        "eu",
        age_group="adult",
        gender="female",
        brand="Anthropologie",
        product_type="shoes",
    )
    assert anthropologie.raw == default.raw

    outfitters = Size.from_raw(16, UK_DRESS_SIZE)
    dresses = outfitters.convert_to_locale(
        "us",
        age_group="adult",
        gender="female",
        brand="Urban Outfitters",
        product_type=ProductType.DRESSES,
    )
    jeans = outfitters.convert_to_locale(
        "us",
        age_group="adult",
        gender="female",
        brand="Urban Outfitters",
        product_type=ProductType.JEANS,
    )
    assert dresses.raw == 16
    assert isinstance(dresses.chart, BrandConversionChart)
    assert jeans.raw == 12
    assert isinstance(jeans.chart, ConversionScale)

    unknown = shoe.convert_to_locale(
        "eu",
        age_group="adult",
        gender="female",
        brand="Not a brand",
        product_type=ProductType.SHOES,
    )
    assert unknown.raw == default.raw
    assert isinstance(unknown.chart, ConversionScale)
    with pytest.raises(ValueError, match="Unknown product type"):
        shoe.convert_to_locale(
            "eu",
            age_group="adult",
            gender="female",
            brand="Dune London",
            product_type="not-a-family",
        )
    with pytest.raises(ValueError, match="brand name"):
        shoe.convert_to_locale(
            "eu",
            age_group="adult",
            gender="female",
            product_type=ProductType.SHOES,
        )
    with pytest.raises(ValueError, match="not both"):
        shoe.convert_to_locale(
            "eu",
            age_group="adult",
            gender="female",
            brand="Dune London",
            product_type=ProductType.SHOES,
            brand_scale=ConversionScale(
                size_type=ADULT_SHOE,
                age_group="adult",
                gender="female",
                rows=(LocaleSizeRow.from_numbers(7, 40, 9, 9),),
            ),
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


def test_chart_with_no_product_types_covers_every_product_type():
    chart = BrandConversionChart(
        brand_name="Example",
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
