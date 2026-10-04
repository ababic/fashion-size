"""Stored codes for a size type.

These are the string values stored for a ``SizeType``. The Django choice
field that uses the same values lives in ``django-fashion-size``.
"""

from enum import StrEnum


class SizeTypeSlug(StrEnum):
    """Fine-grained size types that can be bound to catalog attributes."""

    DRESS = "dress"
    ADULT_SHOE = "adult-shoe"
    KIDS_SHOE = "kids-shoe"
    BABY_SHOE = "baby-shoe"
    CUP_SIZE = "cup-size"
    BAND_SIZE = "band-size"
    WAIST_SIZE = "waist-size"
    CHEST_SIZE = "chest-size"
    CHEST = "chest"
    WAIST = "waist"
    INSIDE_LEG = "inside-leg"
    COLLAR = "collar"
