"""Measurement kind slugs.

These are the string values stored for a measurement kind. The Django choice
field that uses the same values lives in ``django-fashion-size``.
"""

from enum import StrEnum


class KindSlug(StrEnum):
    """Fine-grained measurement kinds that can be bound to catalog attributes."""

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
