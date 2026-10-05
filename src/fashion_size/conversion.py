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
    Size,
    SizeFamily,
    SizeType,
    SizeUnit,
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


def convert(
    value: Size,
    unit: SizeUnit | str,
    *,
    age_group: AgeGroup | str,
    gender: Gender | str,
    brand_name: BrandName | str | None = None,
    product_type: ProductType | str | None = None,
) -> ConvertedSize:
    """Convert ``value`` to ``unit`` on the same size type.

    ``unit`` is any ``SizeUnit`` for this size type, locale-based (``EU_DRESS_SIZE``)
    or a length (``CM_CHEST_SIZE``). ``"cm"`` and ``"in"`` select the length unit.
    ``age_group`` and ``gender`` are required. ``brand_name`` is any brand string.
    A ``BrandName`` selects that brand's chart; any other name uses the default.
    ``product_type`` is a ``ProductType``. Band size always uses the default chart.
    French band size is the EU label plus 15.

    Returns a ``ConvertedSize`` naming the chart that was used. The result cannot
    be converted again.
    """
    if product_type is not None and brand_name is None:
        raise ValueError("A product type needs a brand name.")
    age, sex = resolve_age_gender(age_group, gender)
    known_brand = resolve_brand_name(brand_name) if brand_name is not None else None
    resolved_product_type = (
        resolve_product_type(product_type) if product_type is not None else None
    )
    return _convert(
        value,
        _size_unit_target(value, unit),
        age_group=age,
        gender=sex,
        known_brand=known_brand,
        product_type=resolved_product_type,
    )


def convert_to_locale(
    value: Size,
    locale: Locale | str,
    *,
    age_group: AgeGroup | str,
    gender: Gender | str,
    brand_name: BrandName | str | None = None,
    product_type: ProductType | str | None = None,
) -> ConvertedSize:
    """Convert to the ``SizeUnit`` for ``locale`` on this size type.

    ``locale`` is a ``Locale`` or a slug such as ``"eu"``. This resolves that
    locale to a ``SizeUnit`` and calls ``convert``.
    """
    return convert(
        value,
        size_unit_for_locale(value.size_type, locale),
        age_group=age_group,
        gender=gender,
        brand_name=brand_name,
        product_type=product_type,
    )


def _size_unit_target(value: Size, unit: SizeUnit | str) -> SizeUnit:
    if isinstance(unit, SizeUnit):
        if unit.size_type.slug != value.size_type.slug:
            raise IncompatibleSizeError(
                f"Cannot convert {value.size_type.label} to {unit.label} — size units must share a size type."
            )
        return unit
    return size_unit_for_length_unit(value.size_type, unit)


def _convert(
    value: Size,
    resolved: SizeUnit,
    *,
    age_group: str,
    gender: str,
    known_brand: BrandName | None = None,
    product_type: ProductType | None = None,
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
    if known_brand is not None and value.size_unit.supports_brand_overrides:
        chart = chart_for(
            known_brand,
            value.size_type.slug,
            age_group,
            gender,
            product_type=product_type,
        )
        if chart is None:
            scale = default_scale(value.size_type, age_group, gender)
            used_chart: BrandConversionChart | ConversionScale = scale
        else:
            scale = _scale_from_chart(chart, value.size_type)
            used_chart = chart
    else:
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
