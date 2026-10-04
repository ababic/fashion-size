"""Convert a ``MeasurementValue`` using a formula (length) or a locale chart."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from fashion_size.scales import default_scale
from fashion_size.types import (
    ConversionScale,
    IncompatibleMeasurementError,
    LengthOutOfRangeError,
    Locale,
    Measurement,
    MeasurementFamily,
    MeasurementValue,
    MissingScaleError,
    chart_genders,
    format_age_gender,
    format_raw,
    resolve_age_gender,
    resolve_target_measurement,
)

if TYPE_CHECKING:
    from fashion_size.demographics import AgeGroup, Gender

CM_PER_INCH = Decimal("2.54")
MIN_INCHES = Decimal("5")
MAX_INCHES = Decimal("150")


def convert(
    value: MeasurementValue,
    target: Measurement | Locale | str,
    *,
    age_group: AgeGroup | str | None = None,
    gender: Gender | str | None = None,
    brand_scale: ConversionScale | None = None,
) -> MeasurementValue:
    """Convert ``value`` to ``target`` on the same measurement kind.

    ``target`` may be a concrete ``Measurement``, a chart locale
    (``Locale.EU`` / ``"eu"``), or a length unit (``"cm"`` / ``"in"``).
    Dress, shoe, cup, and band sizes convert across UK/EU/US/AU/FR. Length kinds
    only convert between centimetres and inches. Cross-family targets raise
    ``IncompatibleMeasurementError``.

    Length uses exact ``1 in = 2.54 cm`` for clothing, accessories, and curtains
    (5–150 inches). The converted ``raw`` is not rounded; display rounds
    centimetres to a whole number and inches to the nearest half inch. Dress,
    shoe, cup, and band sizes look up the chart for ``age_group`` and ``gender``
    (the same pair stored on catalogue items). ``brand_scale`` replaces the
    hardcoded default chart for kinds that allow a brand chart. Band size does
    not: it always uses the default chart. French band size is the EU label plus 15.
    """
    resolved = resolve_target_measurement(value.kind, target)
    if not value.measurement.can_convert_to(resolved):
        raise IncompatibleMeasurementError(f"Cannot convert {value.measurement.label} to {resolved.label}.")
    if value.measurement == resolved:
        return value
    if value.kind.family == MeasurementFamily.LENGTH:
        converted = _convert_length(value.raw, value.measurement, resolved)
        return MeasurementValue(raw=converted, measurement=resolved)
    if brand_scale is not None and value.measurement.supports_brand_overrides:
        _validate_brand_scale(brand_scale, value, age_group, gender)
        scale = brand_scale
    else:
        if age_group is None or gender is None:
            raise MissingScaleError("Locale size conversion requires an age group and gender (or a brand_scale).")
        scale = default_scale(value.kind, age_group, gender)
    return MeasurementValue(
        raw=scale.convert_raw(value.raw, value.measurement, resolved),
        measurement=resolved,
    )


def _validate_brand_scale(
    brand_scale: ConversionScale,
    value: MeasurementValue,
    age_group: AgeGroup | str | None,
    gender: Gender | str | None,
) -> None:
    if brand_scale.kind.slug != value.kind.slug:
        raise IncompatibleMeasurementError(f"Brand scale is for {brand_scale.kind.label}, not {value.kind.label}.")
    if age_group is None and gender is None:
        return
    if age_group is None or gender is None:
        raise ValueError("Pass both age_group and gender, or neither.")
    age, sex = resolve_age_gender(age_group, gender)
    if (brand_scale.age_group, brand_scale.gender) not in {(age, candidate) for candidate in chart_genders(age, sex)}:
        raise IncompatibleMeasurementError(
            f"Brand scale is for {format_age_gender(brand_scale.age_group, brand_scale.gender)}, "
            f"not {format_age_gender(age, sex)}."
        )


def _inches_from_length(raw: Decimal, source: Measurement) -> Decimal:
    if source.length_unit == "in":
        return raw
    if source.length_unit == "cm":
        return raw / CM_PER_INCH
    raise IncompatibleMeasurementError(f"Cannot read length from {source.label}.")


def _assert_clothing_length_range(raw: Decimal, source: Measurement) -> None:
    inches = _inches_from_length(raw, source)
    if inches < MIN_INCHES or inches > MAX_INCHES:
        raise LengthOutOfRangeError(
            f"Length {format_raw(raw)}{source.display_suffix or ''} is outside the "
            f"{format_raw(MIN_INCHES)}–{format_raw(MAX_INCHES)} inch clothing range."
        )


def _convert_length(raw: Decimal, source: Measurement, target: Measurement) -> Decimal:
    if source.locale is not Locale.UNIVERSAL or target.locale is not Locale.UNIVERSAL:
        raise IncompatibleMeasurementError(f"Cannot convert length between {source.label} and {target.label}.")
    _assert_clothing_length_range(raw, source)
    if source.length_unit == "in" and target.length_unit == "cm":
        return raw * CM_PER_INCH
    if source.length_unit == "cm" and target.length_unit == "in":
        return raw / CM_PER_INCH
    raise IncompatibleMeasurementError(f"Cannot convert length to {target.label}.")
