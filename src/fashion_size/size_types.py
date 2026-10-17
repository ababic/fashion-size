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
    SHORTS_INSEAM = "shorts-inseam"
    TROUSERS_INSEAM = "trousers-inseam"
    COLLAR = "collar"
    SLEEVE = "sleeve"
    TROUSER_LENGTH = "trouser-length"
    TOP_LENGTH = "top-length"
    SHOE_WIDTH = "shoe-width"
    PROPORTION = "proportion"
    AGE_MONTHS = "age-months"
    AGE_YEARS = "age-years"
    LETTER = "letter"
