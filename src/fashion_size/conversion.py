"""Convert a ``Size`` using a length formula or a locale chart."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from fashion_size.brands import BrandName, resolve_brand_name
from fashion_size.charts import BrandConversionChart, chart_for
from fashion_size.product_types import ProductType, resolve_product_type
from fashion_size.scales import default_scale
from fashion_size.types import (
    ConversionScale,
    IncompatibleSizeError,
    LengthOutOfRangeError,
    LetterSizeRow,
    Locale,
    LocaleSizeRow,
    MissingScaleError,
    Size,
    SizeFamily,
    SizeType,
    SizeUnit,
    chart_genders,
    format_age_gender,
    format_raw,
    resolve_age_gender,
    resolve_target_size_unit,
)

if TYPE_CHECKING:
    from fashion_size.demographics import AgeGroup, Gender

CM_PER_INCH = Decimal("2.54")
MIN_INCHES = Decimal("5")
MAX_INCHES = Decimal("150")


def convert(
    value: Size,
    target: SizeUnit | Locale | str,
    *,
    age_group: AgeGroup | str | None = None,
    gender: Gender | str | None = None,
    brand: BrandName | str | None = None,
    product_type: ProductType | str | None = None,
    brand_scale: ConversionScale | None = None,
) -> Size:
    """Convert ``value`` to ``target`` on the same size type.

    ``target`` may be a concrete ``SizeUnit``, a chart locale
    (``Locale.EU`` / ``"eu"``), or a length unit (``"cm"`` / ``"in"``).
    Dress, shoe, cup, and band sizes convert across UK/EU/US/AU/FR. Length size
    types only convert between centimetres and inches. A target on another size
    type raises ``IncompatibleSizeError``.

    Length uses exact ``1 in = 2.54 cm`` for clothing, accessories, and curtains
    (5–150 inches). The converted ``raw`` is not rounded; display rounds
    centimetres to a whole number and inches to the nearest half inch. Dress,
    shoe, cup, and band sizes look up the chart for ``age_group`` and ``gender``
    (the same pair stored on catalogue items). ``brand`` is any brand string. A
    ``BrandName`` selects that brand's chart; any other name uses the default.
    ``product_type`` is a ``ProductType`` and selects among that brand's charts.
    ``brand_scale`` replaces the chart directly for size types that allow a brand
    chart. Band size does not: it always uses the default chart. French band size
    is the EU label plus 15.
    """
    if brand is not None and brand_scale is not None:
        raise ValueError("Pass a brand name or a brand_scale, not both.")
    if product_type is not None and brand is None:
        raise ValueError("A product type needs a brand name.")
    known_brand = resolve_brand_name(brand) if brand is not None else None
    resolved_product_type = (
        resolve_product_type(product_type) if product_type is not None else None
    )
    resolved = resolve_target_size_unit(value.size_type, target)
    if not value.size_unit.can_convert_to(resolved):
        raise IncompatibleSizeError(
            f"Cannot convert {value.size_unit.label} to {resolved.label}."
        )
    if value.size_unit == resolved:
        return value
    if value.size_type.family == SizeFamily.LENGTH:
        converted = _convert_length(value.raw, value.size_unit, resolved)
        return Size(raw=converted, size_unit=resolved)
    if brand_scale is not None and value.size_unit.supports_brand_overrides:
        _validate_brand_scale(brand_scale, value, age_group, gender)
        scale = brand_scale
    elif known_brand is not None and value.size_unit.supports_brand_overrides:
        if age_group is None or gender is None:
            raise MissingScaleError(
                "Locale size conversion requires an age group and gender (or a brand_scale)."
            )
        chart = chart_for(
            known_brand,
            value.size_type.slug,
            age_group,
            gender,
            product_type=resolved_product_type,
        )
        if chart is None:
            scale = default_scale(value.size_type, age_group, gender)
        else:
            scale = _scale_from_chart(chart, value.size_type)
            _validate_brand_scale(scale, value, age_group, gender)
    else:
        if age_group is None or gender is None:
            raise MissingScaleError(
                "Locale size conversion requires an age group and gender (or a brand_scale)."
            )
        scale = default_scale(value.size_type, age_group, gender)
    return Size(
        raw=scale.convert_raw(value.raw, value.size_unit, resolved),
        size_unit=resolved,
    )


def _scale_from_chart(chart: BrandConversionChart, size_type: SizeType) -> ConversionScale:
    """Turn a shipped brand chart into the scale ``convert`` looks up."""
    if size_type.family == SizeFamily.CUP_SIZE:
        rows = tuple(
            LetterSizeRow.from_tokens(row["uk"], row["eu"], row["us"], row["au"])
            for row in chart.rows
        )
    else:
        rows = tuple(
            LocaleSizeRow.from_numbers(row["uk"], row["eu"], row["us"], row["au"])
            for row in chart.rows
        )
    return ConversionScale(
        size_type=size_type,
        age_group=chart.age_group,
        gender=chart.gender,
        rows=rows,
    )


def _validate_brand_scale(
    brand_scale: ConversionScale,
    value: Size,
    age_group: AgeGroup | str | None,
    gender: Gender | str | None,
) -> None:
    if brand_scale.size_type.slug != value.size_type.slug:
        raise IncompatibleSizeError(
            f"Brand scale is for {brand_scale.size_type.label}, not {value.size_type.label}."
        )
    if age_group is None and gender is None:
        return
    if age_group is None or gender is None:
        raise ValueError("Pass both age_group and gender, or neither.")
    age, sex = resolve_age_gender(age_group, gender)
    if (brand_scale.age_group, brand_scale.gender) not in {
        (age, candidate) for candidate in chart_genders(age, sex)
    }:
        raise IncompatibleSizeError(
            f"Brand scale is for {format_age_gender(brand_scale.age_group, brand_scale.gender)}, "
            f"not {format_age_gender(age, sex)}."
        )


def _inches_from_length(raw: Decimal, source: SizeUnit) -> Decimal:
    if source.length_unit == "in":
        return raw
    if source.length_unit == "cm":
        return raw / CM_PER_INCH
    raise IncompatibleSizeError(f"Cannot read length from {source.label}.")


def _assert_clothing_length_range(raw: Decimal, source: SizeUnit) -> None:
    inches = _inches_from_length(raw, source)
    if inches < MIN_INCHES or inches > MAX_INCHES:
        raise LengthOutOfRangeError(
            f"Length {format_raw(raw)}{source.display_suffix or ''} is outside the "
            f"{format_raw(MIN_INCHES)}–{format_raw(MAX_INCHES)} inch clothing range."
        )


def _convert_length(raw: Decimal, source: SizeUnit, target: SizeUnit) -> Decimal:
    if source.locale is not Locale.UNIVERSAL or target.locale is not Locale.UNIVERSAL:
        raise IncompatibleSizeError(
            f"Cannot convert length between {source.label} and {target.label}."
        )
    _assert_clothing_length_range(raw, source)
    if source.length_unit == "in" and target.length_unit == "cm":
        return raw * CM_PER_INCH
    if source.length_unit == "cm" and target.length_unit == "in":
        return raw / CM_PER_INCH
    raise IncompatibleSizeError(f"Cannot convert length to {target.label}.")
