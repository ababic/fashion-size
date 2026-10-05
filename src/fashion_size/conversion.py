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
    ConvertedSize,
    IncompatibleSizeError,
    LengthFormula,
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
    size_unit_for_length_unit,
    size_unit_for_locale,
)

if TYPE_CHECKING:
    from fashion_size.demographics import AgeGroup, Gender

CM_PER_INCH = Decimal("2.54")
MIN_INCHES = Decimal("5")
MAX_INCHES = Decimal("150")


def convert_to_unit(value: Size, unit: SizeUnit | str) -> ConvertedSize:
    """Convert a length between centimetres and inches.

    ``unit`` is ``"cm"``, ``"in"``, or a length ``SizeUnit`` on the same size type.
    Chart locales use ``convert_to_locale``. A converted length records a
    ``LengthFormula``. The result cannot be converted again.
    """
    return _convert(value, _length_target(value, unit))


def convert_to_locale(
    value: Size,
    locale: SizeUnit | Locale | str,
    *,
    age_group: AgeGroup | str | None = None,
    gender: Gender | str | None = None,
    brand: BrandName | str | None = None,
    product_type: ProductType | str | None = None,
    brand_scale: ConversionScale | None = None,
) -> ConvertedSize:
    """Convert ``value`` to a UK / EU / US / AU / FR size on the same size type.

    ``locale`` is a ``Locale``, a slug such as ``"eu"``, or a locale ``SizeUnit``
    on the same size type. Lengths use ``convert_to_unit``. ``age_group`` and
    ``gender`` select the chart. ``brand`` is any brand string. A ``BrandName``
    selects that brand's chart; any other name uses the default. ``product_type``
    is a ``ProductType``. ``brand_scale`` replaces the chart directly when the
    size type allows it. Band size always uses the default chart. French band
    size is the EU label plus 15.

    Returns a ``ConvertedSize`` naming the chart that was used. The result cannot
    be converted again.
    """
    if brand is not None and brand_scale is not None:
        raise ValueError("Pass a brand name or a brand_scale, not both.")
    if product_type is not None and brand is None:
        raise ValueError("A product type needs a brand name.")
    known_brand = resolve_brand_name(brand) if brand is not None else None
    resolved_product_type = (
        resolve_product_type(product_type) if product_type is not None else None
    )
    return _convert(
        value,
        _locale_target(value, locale),
        age_group=age_group,
        gender=gender,
        known_brand=known_brand,
        product_type=resolved_product_type,
        brand_scale=brand_scale,
    )


def _length_target(value: Size, unit: SizeUnit | str) -> SizeUnit:
    if isinstance(unit, SizeUnit):
        if unit.length_unit is None:
            raise IncompatibleSizeError(
                f"Cannot convert {value.size_unit.label} to {unit.label} with convert_to_unit. "
                "Use convert_to_locale."
            )
        if unit.size_type.slug != value.size_type.slug:
            raise IncompatibleSizeError(
                f"Cannot convert {value.size_type.label} to {unit.label} — size units must share a size type."
            )
        return unit
    return size_unit_for_length_unit(value.size_type, unit)


def _locale_target(value: Size, locale: SizeUnit | Locale | str) -> SizeUnit:
    if isinstance(locale, SizeUnit):
        if locale.length_unit is not None:
            raise IncompatibleSizeError(
                f"Cannot convert {value.size_unit.label} to {locale.label} with convert_to_locale. "
                "Use convert_to_unit."
            )
        if locale.size_type.slug != value.size_type.slug:
            raise IncompatibleSizeError(
                f"Cannot convert {value.size_type.label} to {locale.label} — size units must share a size type."
            )
        return locale
    return size_unit_for_locale(value.size_type, locale)


def _convert(
    value: Size,
    resolved: SizeUnit,
    *,
    age_group: AgeGroup | str | None = None,
    gender: Gender | str | None = None,
    known_brand: BrandName | None = None,
    product_type: ProductType | None = None,
    brand_scale: ConversionScale | None = None,
) -> ConvertedSize:
    if not value.size_unit.can_convert_to(resolved):
        raise IncompatibleSizeError(
            f"Cannot convert {value.size_unit.label} to {resolved.label}."
        )
    if value.size_unit == resolved:
        return ConvertedSize(size=value, chart=None)
    if value.size_type.family == SizeFamily.LENGTH:
        converted = _convert_length(value.raw, value.size_unit, resolved)
        return ConvertedSize(
            size=Size(raw=converted, size_unit=resolved),
            chart=LengthFormula(),
        )
    if brand_scale is not None and value.size_unit.supports_brand_overrides:
        _validate_brand_scale(brand_scale, value, age_group, gender)
        scale = brand_scale
        used_chart: BrandConversionChart | ConversionScale = brand_scale
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
            product_type=product_type,
        )
        if chart is None:
            scale = default_scale(value.size_type, age_group, gender)
            used_chart = scale
        else:
            scale = _scale_from_chart(chart, value.size_type)
            _validate_brand_scale(scale, value, age_group, gender)
            used_chart = chart
    else:
        if age_group is None or gender is None:
            raise MissingScaleError(
                "Locale size conversion requires an age group and gender (or a brand_scale)."
            )
        scale = default_scale(value.size_type, age_group, gender)
        used_chart = scale
    return ConvertedSize(
        size=Size(
            raw=scale.convert_raw(value.raw, value.size_unit, resolved),
            size_unit=resolved,
        ),
        chart=used_chart,
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
