"""Behaviour covered by the README and the charts shipped in the package."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from fashion_size import (
    SUPPORTED_BRANDS,
    OverrideGuide,
    __version__,
    register_brand_converter,
    register_display_language,
)
from fashion_size.charts import (
    BrandConversionChart,
    _parse_chart,
    chart_for,
    charts_for_brand,
    load_brand_charts,
)
from fashion_size.kinds import KindSlug
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
    IncompatibleMeasurementError,
    LengthOutOfRangeError,
    LocaleSizeRow,
    MeasurementValue,
    MissingScaleError,
    UnknownSizeError,
    measurement_choices_for_kind,
    measurement_value_from_attribute_option,
    parse_measurement_slug,
)


def test_version_is_the_initial_release():
    assert __version__ == "0.1.0"


def test_readme_brand_chart_example():
    assert "Dune London" in SUPPORTED_BRANDS
    chart = chart_for("Dune London", "adult-shoe", "adult", "female", guide=OverrideGuide.SHOES)
    assert chart is not None
    assert chart.updated_at == datetime(2026, 3, 29, tzinfo=UTC)
    assert chart.source_url == "https://www.dunelondon.com/size-guide"
    assert chart.source_notes == ""
    assert {"uk": 7, "eu": 40, "us": 9, "au": 9} in chart.rows
    assert chart.covers(OverrideGuide.SHOES)
    assert not chart.covers(OverrideGuide.JEANS)


def test_readme_dress_conversion():
    value = MeasurementValue.from_raw("10", UK_DRESS_SIZE)
    converted = value.convert("eu", age_group="adult", gender="female")
    assert converted == MeasurementValue.from_raw(38, EU_DRESS_SIZE)
    assert str(converted) == "EU 38"
    assert str(value) == "UK 10"


def test_locale_charts():
    women_10 = MeasurementValue.from_raw("10", UK_DRESS_SIZE)
    assert women_10.convert("us", age_group="adult", gender="female").raw == 6
    assert women_10.convert("au", age_group="adult", gender="female").raw == 10
    french = women_10.convert("fr", age_group="adult", gender="female")
    assert french.measurement is EU_DRESS_SIZE
    assert french.raw == 38
    assert str(french) == "EU 38"

    assert MeasurementValue.from_raw(38, UK_DRESS_SIZE).convert("eu", age_group="adult", gender="male").raw == 48
    assert MeasurementValue.from_raw(38, UK_DRESS_SIZE).convert("eu", age_group="adult", gender="unisex").raw == 48
    assert MeasurementValue.from_raw(8, UK_DRESS_SIZE).convert("eu", age_group="child", gender="female").raw == 128

    women_shoe = MeasurementValue.from_raw(7, UK_ADULT_SHOE_SIZE)
    assert women_shoe.convert("eu", age_group="adult", gender="female").raw == 41
    assert women_shoe.convert("us", age_group="adult", gender="female").raw == 9
    assert women_shoe.convert("au", age_group="adult", gender="female").raw == 9
    half = MeasurementValue.from_raw("7.5", UK_ADULT_SHOE_SIZE).convert("eu", age_group="adult", gender="female")
    assert half.raw == Decimal("41.5")
    assert str(half) == "EU 41.5"

    men_shoe = MeasurementValue.from_raw(7, UK_ADULT_SHOE_SIZE)
    assert men_shoe.convert("us", age_group="adult", gender="male").raw == 8
    assert men_shoe.convert("au", age_group="adult", gender="unisex").raw == 7
    assert MeasurementValue.from_raw(6, UK_KIDS_SHOE_SIZE).convert("eu", age_group="child", gender="male").raw == 23
    assert MeasurementValue.from_raw(0, UK_BABY_SHOE_SIZE).convert("eu", age_group="baby", gender="unisex").raw == 16

    band = MeasurementValue.from_raw(34, UK_BAND_SIZE)
    assert band.convert("eu", age_group="adult", gender="female") == MeasurementValue.from_raw(75, EU_BAND_SIZE)
    assert band.convert("au", age_group="adult", gender="male").raw == 12
    assert band.convert("fr", age_group="adult", gender="female") == MeasurementValue.from_raw(90, FR_BAND_SIZE)
    assert MeasurementValue.from_raw(90, FR_BAND_SIZE).convert("uk", age_group="adult", gender="female").raw == 34

    assert MeasurementValue.from_raw(32, UK_WAIST_SIZE).convert("eu", age_group="adult", gender="male").raw == 48
    assert MeasurementValue.from_raw(40, UK_CHEST_SIZE).convert("eu", age_group="adult", gender="male").raw == 50
    assert MeasurementValue.from_raw(22, UK_WAIST_SIZE).convert("eu", age_group="child", gender="male").raw == 56

    cup = MeasurementValue.from_raw("dd", UK_CUP_SIZE)
    assert str(cup) == "DD"
    assert cup.convert("eu", age_group="adult", gender="female").raw == "E"
    assert MeasurementValue.from_raw("E", UK_CUP_SIZE).convert("us", age_group="adult", gender="female").raw == "DDD"


def test_length_conversion_and_display():
    inches = MeasurementValue.from_raw(32, INCH_CHEST_SIZE)
    centimetres = inches.convert("cm")
    assert centimetres.measurement is CM_CHEST_SIZE
    assert centimetres.raw == Decimal("81.28")
    assert centimetres.localised_display("en-gb") == "81cm"
    assert centimetres.localised_display("de") == "81 cm"
    assert inches.localised_display("en-us") == '32"'
    assert inches.localised_display("fr") == "32 in"
    assert centimetres.convert("in").raw == Decimal("32")

    assert MeasurementValue.from_raw(5, INCH_CHEST_SIZE).convert("cm").raw == Decimal("12.7")
    assert MeasurementValue.from_raw(150, INCH_CHEST_SIZE).convert("cm").raw == Decimal("381")
    assert MeasurementValue.from_raw(Decimal("10.3"), INCH_CHEST_SIZE).localised_display() == '10.5"'
    assert MeasurementValue.from_raw(Decimal("10.5"), CM_CHEST_SIZE).localised_display("de") == "11 cm"

    register_display_language(lambda: "de")
    assert str(inches) == "32 in"
    assert inches.localised_display("en-gb") == '32"'


def test_conversion_rejects_unknown_or_incompatible_values():
    with pytest.raises(UnknownSizeError):
        MeasurementValue.from_raw(11, UK_DRESS_SIZE).convert("eu", age_group="adult", gender="female")
    with pytest.raises(UnknownSizeError):
        MeasurementValue.from_raw(10, UK_DRESS_SIZE).convert("eu", age_group="adult", gender="male")
    with pytest.raises(MissingScaleError):
        MeasurementValue.from_raw(10, UK_DRESS_SIZE).convert("eu")
    with pytest.raises(MissingScaleError):
        MeasurementValue.from_raw(62, UK_DRESS_SIZE).convert("eu", age_group="baby", gender="unisex")
    with pytest.raises(ValueError, match="French|locale 'fr'|No Waist size"):
        MeasurementValue.from_raw(32, UK_WAIST_SIZE).convert("fr", age_group="adult", gender="male")
    with pytest.raises(IncompatibleMeasurementError):
        MeasurementValue.from_raw(10, UK_DRESS_SIZE).convert(EU_ADULT_SHOE_SIZE, age_group="adult", gender="female")
    with pytest.raises(IncompatibleMeasurementError):
        MeasurementValue.from_raw(32, INCH_CHEST_SIZE).convert("eu")
    with pytest.raises(IncompatibleMeasurementError):
        MeasurementValue.from_raw(10, UK_DRESS_SIZE).convert("cm", age_group="adult", gender="female")
    with pytest.raises(LengthOutOfRangeError):
        MeasurementValue.from_raw(Decimal("4.9"), INCH_CHEST_SIZE).convert("cm")
    with pytest.raises(LengthOutOfRangeError):
        MeasurementValue.from_raw(Decimal("12.69"), CM_CHEST_SIZE).convert("in")
    with pytest.raises(LengthOutOfRangeError):
        MeasurementValue.from_raw(Decimal("150.1"), INCH_CHEST_SIZE).convert("cm")
    with pytest.raises(ValueError, match="cup"):
        MeasurementValue.from_raw("D-E", UK_CUP_SIZE)

    same = MeasurementValue.from_raw(10, UK_DRESS_SIZE)
    assert same.convert(UK_DRESS_SIZE) is same


def test_brand_scale_replaces_the_default_chart_when_the_kind_allows_it():
    dune = ConversionScale(
        kind=ADULT_SHOE,
        age_group="adult",
        gender="female",
        rows=(LocaleSizeRow.from_numbers(7, 40, 9, 9),),
    )
    converted = MeasurementValue.from_raw(7, UK_ADULT_SHOE_SIZE).convert(
        "eu",
        age_group="adult",
        gender="female",
        brand_scale=dune,
    )
    assert converted.raw == 40

    ignored = ConversionScale(
        kind=BAND_SIZE,
        age_group="adult",
        gender="female",
        rows=(LocaleSizeRow.from_numbers(34, 1, 1, 1),),
    )
    assert MeasurementValue.from_raw(34, UK_BAND_SIZE).convert(
        "eu",
        age_group="adult",
        gender="female",
        brand_scale=ignored,
    ).raw == 75

    with pytest.raises(IncompatibleMeasurementError):
        MeasurementValue.from_raw(10, UK_DRESS_SIZE).convert("eu", age_group="adult", gender="female", brand_scale=dune)
    with pytest.raises(ValueError, match="both"):
        MeasurementValue.from_raw(7, UK_ADULT_SHOE_SIZE).convert("eu", age_group="adult", brand_scale=dune)


def test_attribute_options_and_measurement_slugs():
    dress = measurement_value_from_attribute_option("uk-dress-size", "UK 10")
    assert dress is not None and dress.raw == 10 and dress.measurement is UK_DRESS_SIZE
    prefixed = measurement_value_from_attribute_option("uk-dress-size", "Size 10", raw_value_prefix="Size ")
    assert prefixed is not None and prefixed.raw == 10
    chest = measurement_value_from_attribute_option("in-chest-size", '32"')
    assert chest is not None and chest.raw == 32 and chest.measurement is INCH_CHEST_SIZE
    cup = measurement_value_from_attribute_option("uk-cup-size", "dd")
    assert cup is not None and cup.raw == "DD"
    assert measurement_value_from_attribute_option("uk-dress-size", "small") is None
    assert measurement_value_from_attribute_option("not-a-size", "10") is None

    assert parse_measurement_slug("fr-dress-size") is EU_DRESS_SIZE
    assert parse_measurement_slug("fr-band-size") is FR_BAND_SIZE
    assert FR_BAND_SIZE is not EU_BAND_SIZE
    with pytest.raises(ValueError, match="Unknown measurement"):
        parse_measurement_slug("xx-dress-size")
    assert "uk-dress-size" in dict(measurement_choices_for_kind("dress"))
    assert "uk-adult-shoe-size" not in dict(measurement_choices_for_kind("dress"))


def test_brand_converter_hook():
    value = MeasurementValue.from_raw(10, UK_DRESS_SIZE)
    with pytest.raises(RuntimeError, match="register_brand_converter"):
        value.convert_to_locale(None, "eu", brand="Dune London", age_group="adult", gender="female")

    seen = {}

    def converter(measurement, target_locale, *, age_group, gender, brand, product_type_group):
        seen.update(
            age_group=age_group,
            gender=gender,
            brand=brand,
            product_type_group=product_type_group,
            target_locale=target_locale,
        )
        return measurement.convert(target_locale, age_group=age_group, gender=gender)

    register_brand_converter(converter)
    converted = value.convert_to_locale(7, "eu", brand="Dune London", age_group="adult", gender="female")
    assert converted.raw == 38
    assert seen == {
        "age_group": "adult",
        "gender": "female",
        "brand": "Dune London",
        "product_type_group": 7,
        "target_locale": "eu",
    }


def test_shipped_brand_charts_are_complete():
    charts = load_brand_charts()
    assert charts
    assert {chart.brand_name for chart in charts} <= set(SUPPORTED_BRANDS)
    assert charts_for_brand("finisterre") == ()
    assert charts_for_brand("  dune LONDON ")[0].brand_name == "Dune London"

    for chart in charts:
        assert chart.kind in KindSlug
        assert chart.updated_at.tzinfo is not None
        assert chart.rows
        guide = chart.guides[0] if chart.guides else None
        gender = chart.gender or "female"
        found = chart_for(chart.brand_name, chart.kind, chart.age_group, gender, guide=guide)
        assert found is chart

    kids = chart_for("Salt-Water Sandals", "kids-shoe", "child", "male", guide=OverrideGuide.SHOES)
    assert kids is not None and kids.gender == ""
    jeans = chart_for("Urban Outfitters", "dress", "adult", "female", guide=OverrideGuide.JEANS)
    assert jeans is None
    dresses = chart_for("Urban Outfitters", "dress", "adult", " Female ", guide="dresses")
    assert dresses is not None and dresses.covers("dresses")


def test_chart_with_no_guides_covers_every_family():
    chart = BrandConversionChart(
        brand_name="Example",
        kind="dress",
        age_group="adult",
        gender="female",
        guides=(),
        updated_at=datetime(2026, 3, 29, tzinfo=UTC),
        source_url="",
        source_notes="",
        rows=({"uk": 10, "eu": 38, "us": 6, "au": 10},),
    )
    assert chart.covers("jeans")
    assert chart.covers("shoes")


def _chart_entry(**overrides):
    entry = {
        "brand_name": "Example",
        "kind": "adult-shoe",
        "age_group": "adult",
        "gender": "female",
        "guides": ["shoes"],
        "updated_at": "2026-03-29T00:00:00Z",
        "source_url": "https://example.com/size-guide",
        "rows": [{"uk": 7, "eu": 40, "us": 9, "au": 9}],
    }
    entry.update(overrides)
    return entry


@pytest.mark.parametrize(
    ("overrides", "match"),
    [
        ({"brand_name": "  "}, "brand_name"),
        ({"kind": "hat"}, "measurement kind"),
        ({"age_group": "teen"}, "age group"),
        ({"gender": "unisex"}, "gender"),
        ({"guides": ["not-a-family"]}, "override guides"),
        ({"rows": []}, "no rows"),
        ({"rows": [{"uk": 7, "eu": 40}]}, "uk, eu, us, and au"),
        ({"rows": [{"uk": True, "eu": 40, "us": 9, "au": 9}]}, "invalid"),
        ({"updated_at": "2026-03-29T00:00:00"}, "timezone"),
    ],
)
def test_chart_fixture_rows_are_rejected_when_incomplete(overrides, match):
    with pytest.raises(ValueError, match=match):
        _parse_chart(_chart_entry(**overrides))
