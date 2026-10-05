"""Hardcoded default locale conversion charts.

These are industry-common approximations, not brand truth. Brand-specific charts
live in ``fashion_size.charts``. ``convert_to_locale(..., brand_name=..., product_type=...)``
looks them up by brand name.

Charts are keyed by the same ``age_group`` × ``gender`` pair used on catalogue
items. Row order is ``(uk, eu, us, au)``.

Sources checked (UK high-street guides first, since brand feeds follow them):

* Clothing — ASOS, Next, and Nike UK size guides; Wikipedia "Clothing sizes".
* Shoes — Clarks UK fit guide (adult, kids, and babies), M&S and Next women's
  footwear guides, ISO/TS 19407 tables via Wikipedia "Shoe size".
* Australia — Wikipedia "Shoe size": AU follows UK for men's and children's
  footwear and US for women's. AU clothing is labelled with UK sizes.
* Cup sizes — Freya, Fantasie, and Panache international converters.
* Bra bands — UK and US share the inch number (28 = 28). EU is the centimetre
  label (UK 34 = 75). Australia uses the even dress-style number (UK 34 = 12).
  French is not a column: FR = EU + 15. The same chart is used for every adult.

Where UK guides disagree by half a shoe size, the UK → EU column is the same
for every age group (EU sizes are unisex and UK sizes share one length scale).
"""

from __future__ import annotations

from fashion_size.demographics import AgeGroup, Gender
from fashion_size.types import (
    ADULT_SHOE,
    BABY_SHOE,
    BAND_SIZE,
    CHEST_SIZE,
    CUP_SIZE,
    DRESS,
    KIDS_SHOE,
    WAIST_SIZE,
    ConversionScale,
    LetterSizeRow,
    LocaleSizeRow,
    MissingScaleError,
    SizeType,
    chart_genders,
    format_age_gender,
    resolve_age_gender,
)

_Number = int | float


def _scale(
    size_type: SizeType,
    age_group: str,
    gender: str,
    rows: tuple[tuple[_Number, _Number, _Number, _Number], ...],
) -> ConversionScale:
    return ConversionScale(
        size_type=size_type,
        age_group=age_group,
        gender=gender,
        rows=tuple(LocaleSizeRow.from_numbers(*row) for row in rows),
    )


# Women's clothing: EU = UK + 28, US = UK - 4, AU = UK. Australian women's sizes
# use the UK numbers (ASOS, Next, and Nike UK guides all list AU 8 = UK 8 = US 4 = EU 36).
_WOMEN_DRESS_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = tuple(
    (uk, uk + 28, uk - 4, uk) for uk in range(4, 34, 2)
)

# Men's waist label: US/AU = UK inch waist, EU/IT = UK + 16 (30 → 46, 31 → 47).
# Every whole inch is a real label. Brands that only print even sizes still match;
# brands that print 37" or 39" convert on the same offset.
_MENS_WAIST_SIZE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = tuple(
    (uk, uk + 16, uk, uk) for uk in range(28, 57)
)

# Men's chest / jacket label: US/AU = UK inch chest, EU/IT = UK + 10 (38 → 48, 39 → 49).
# Every whole inch, for the same reason as waist.
_MENS_CHEST_SIZE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = tuple(
    (uk, uk + 10, uk, uk) for uk in range(30, 57)
)

# Kids' trousers and blazers are labelled "to fit" in inches in the UK, US, and
# AU (school uniform 22" to 34"). EU children's sizes are height, not a waist or
# chest label, so the EU column holds the same measurement in whole centimetres.
_KIDS_WAIST_SIZE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = tuple(
    (uk, round(uk * 2.54), uk, uk) for uk in range(18, 37)
)
_KIDS_CHEST_SIZE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = tuple(
    (uk, round(uk * 2.54), uk, uk) for uk in range(20, 39)
)

# Men's jacket / numeric clothing: US/AU = UK, EU = UK + 10.
_MEN_DRESS_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = (
    (32, 42, 32, 32),
    (34, 44, 34, 34),
    (36, 46, 36, 36),
    (38, 48, 38, 38),
    (40, 50, 40, 40),
    (42, 52, 42, 42),
    (44, 54, 44, 44),
    (46, 56, 46, 46),
    (48, 58, 48, 48),
    (50, 60, 50, 50),
)

# Girls / boys numeric clothing: the UK and AU label is the age; EU is height in cm
# (age 2 = 92, then 6 cm per year). US uses the same age numbers as a nearest
# match — US labels are really 2T–4T then 5–7 and even sizes 8–16.
_KIDS_DRESS_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = (
    (2, 92, 2, 2),
    (3, 98, 3, 3),
    (4, 104, 4, 4),
    (5, 110, 5, 5),
    (6, 116, 6, 6),
    (7, 122, 7, 7),
    (8, 128, 8, 8),
    (9, 134, 9, 9),
    (10, 140, 10, 10),
    (11, 146, 11, 11),
    (12, 152, 12, 12),
    (13, 158, 13, 13),
    (14, 164, 14, 14),
)

# Women's shoes: US = UK + 2, and Australian women's shoes use the US numbers.
# UK → EU follows Clarks / M&S / Next (UK 3 = 35.5, 4 = 37, 5 = 38, 6 = 39, 7 = 41,
# 8 = 42). ASOS alone lists UK 7 = 40 and UK 8 = 41; brands that size that way can
# save their own chart.
_WOMEN_SHOE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = (
    (2, 34, 4, 4),
    (2.5, 35, 4.5, 4.5),
    (3, 35.5, 5, 5),
    (3.5, 36, 5.5, 5.5),
    (4, 37, 6, 6),
    (4.5, 37.5, 6.5, 6.5),
    (5, 38, 7, 7),
    (5.5, 38.5, 7.5, 7.5),
    (6, 39, 8, 8),
    (6.5, 40, 8.5, 8.5),
    (7, 41, 9, 9),
    (7.5, 41.5, 9.5, 9.5),
    (8, 42, 10, 10),
    (8.5, 42.5, 10.5, 10.5),
    (9, 43, 11, 11),
)

# Men's shoes: AU = UK, US = UK + 1. UK → EU follows Clarks (UK 7 = 41, 8 = 42,
# 9 = 43, 9.5 = 44, 10 = 44.5, 11 = 46, 12 = 47, 12.5 = 47.5, 13 = 48).
_MEN_SHOE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = (
    (5, 38, 6, 5),
    (5.5, 38.5, 6.5, 5.5),
    (6, 39, 7, 6),
    (6.5, 40, 7.5, 6.5),
    (7, 41, 8, 7),
    (7.5, 41.5, 8.5, 7.5),
    (8, 42, 9, 8),
    (8.5, 42.5, 9.5, 8.5),
    (9, 43, 10, 9),
    (9.5, 44, 10.5, 9.5),
    (10, 44.5, 11, 10),
    (10.5, 45, 11.5, 10.5),
    (11, 46, 12, 11),
    (11.5, 46.5, 12.5, 11.5),
    (12, 47, 13, 12),
    (12.5, 47.5, 13.5, 12.5),
    (13, 48, 14, 13),
)

# Kids shoes (UK 6–13 then youth 1–5.5). Separate from baby and adult size types.
# AU = UK (Australian children's shoes use UK numbers), US = UK + 1. UK → EU follows
# the Clarks kids chart; UK 2.5–5.5 match the adult chart for the same UK size.
_KIDS_SHOE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = (
    (6, 23, 7, 6),
    (6.5, 23.5, 7.5, 6.5),
    (7, 24, 8, 7),
    (7.5, 25, 8.5, 7.5),
    (8, 25.5, 9, 8),
    (8.5, 26, 9.5, 8.5),
    (9, 27, 10, 9),
    (9.5, 27.5, 10.5, 9.5),
    (10, 28, 11, 10),
    (10.5, 28.5, 11.5, 10.5),
    (11, 29, 12, 11),
    (11.5, 29.5, 12.5, 11.5),
    (12, 30, 13, 12),
    (12.5, 31, 13.5, 12.5),
    (13, 32, 1, 13),
    (13.5, 32.5, 1.5, 13.5),
    (1, 33, 2, 1),
    (1.5, 33.5, 2.5, 1.5),
    (2, 34, 3, 2),
    (2.5, 35, 3.5, 2.5),
    (3, 35.5, 4, 3),
    (3.5, 36, 4.5, 3.5),
    (4, 37, 5, 4),
    (4.5, 37.5, 5.5, 4.5),
    (5, 38, 6, 5),
    (5.5, 38.5, 6.5, 5.5),
)

# Baby shoes. Not gendered unless a brand adds a boys or girls row.
# AU = UK, US = UK + 1. UK → EU follows the Clarks babies chart (UK 3 = 19, 4 = 20,
# 5 = 21, 5.5 = 22), which leads into the kids chart at UK 6 = 23.
_BABY_SHOE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = (
    (0, 16, 1, 0),
    (0.5, 16.5, 1.5, 0.5),
    (1, 17, 2, 1),
    (1.5, 17.5, 2.5, 1.5),
    (2, 18, 3, 2),
    (2.5, 18.5, 3.5, 2.5),
    (3, 19, 4, 3),
    (3.5, 19.5, 4.5, 3.5),
    (4, 20, 5, 4),
    (4.5, 20.5, 5.5, 4.5),
    (5, 21, 6, 5),
    (5.5, 22, 6.5, 5.5),
)

# Bra band, even inches 28–56. UK = US. EU = UK × 2.5 − 10. AU = UK − 22.
# One chart for every adult. Brands do not replace it.
_BAND_SIZE_ROWS: tuple[tuple[_Number, _Number, _Number, _Number], ...] = tuple(
    (uk, uk * 5 // 2 - 10, uk, uk - 22) for uk in range(28, 57, 2)
)

# UK and AU share letters. EU steps to a single letter after D (DD → E).
# US matches UK through DD, then DDD for UK E, and single letters from G (UK F).
# Same mapping as the Freya, Fantasie, and Panache international converters.
_CUP_SIZE_ROWS: tuple[tuple[str, str, str, str], ...] = (
    ("AA", "AA", "AA", "AA"),
    ("A", "A", "A", "A"),
    ("B", "B", "B", "B"),
    ("C", "C", "C", "C"),
    ("D", "D", "D", "D"),
    ("DD", "E", "DD", "DD"),
    ("E", "F", "DDD", "E"),
    ("F", "G", "G", "F"),
    ("FF", "H", "H", "FF"),
    ("G", "I", "I", "G"),
    ("GG", "J", "J", "GG"),
    ("H", "K", "K", "H"),
    ("HH", "L", "L", "HH"),
    ("J", "M", "M", "J"),
    ("JJ", "N", "N", "JJ"),
    ("K", "O", "O", "K"),
)


def _letter_scale(
    size_type: SizeType,
    age_group: str,
    gender: str,
    rows: tuple[tuple[str, str, str, str], ...],
) -> ConversionScale:
    return ConversionScale(
        size_type=size_type,
        age_group=age_group,
        gender=gender,
        rows=tuple(LetterSizeRow.from_tokens(*row) for row in rows),
    )


def _letter_charts(
    size_type: SizeType,
    pairs: tuple[tuple[str, str], ...],
    rows: tuple[tuple[str, str, str, str], ...],
) -> dict[tuple[str, str, str], ConversionScale]:
    return {
        (size_type.slug, age, sex): _letter_scale(size_type, age, sex, rows)
        for age, sex in pairs
    }


def _charts(
    size_type: SizeType,
    pairs: tuple[tuple[str, str], ...],
    rows: tuple[tuple[_Number, _Number, _Number, _Number], ...],
) -> dict[tuple[str, str, str], ConversionScale]:
    return {
        (size_type.slug, age, sex): _scale(size_type, age, sex, rows)
        for age, sex in pairs
    }


_ADULT_FEMALE = (AgeGroup.ADULT, Gender.FEMALE)
_ADULT_MALE = (AgeGroup.ADULT, Gender.MALE)
_CHILD_ALL = (AgeGroup.CHILD, "")
_BABY_ALL = (AgeGroup.BABY, "")

DEFAULT_SCALES: dict[tuple[str, str, str], ConversionScale] = {
    **_charts(DRESS, (_ADULT_FEMALE,), _WOMEN_DRESS_ROWS),
    **_charts(DRESS, (_ADULT_MALE,), _MEN_DRESS_ROWS),
    # One kids chart. A brand can still store separate boys and girls rows.
    **_charts(DRESS, (_CHILD_ALL,), _KIDS_DRESS_ROWS),
    **_charts(ADULT_SHOE, (_ADULT_FEMALE,), _WOMEN_SHOE_ROWS),
    **_charts(ADULT_SHOE, (_ADULT_MALE,), _MEN_SHOE_ROWS),
    **_charts(KIDS_SHOE, (_CHILD_ALL,), _KIDS_SHOE_ROWS),
    # Baby shoe charts are not gendered unless a brand adds a boys or girls row.
    **_charts(BABY_SHOE, (_BABY_ALL,), _BABY_SHOE_ROWS),
    # Adult women. A brand can add a product-type-group chart (bras vs swimwear).
    **_letter_charts(CUP_SIZE, (_ADULT_FEMALE,), _CUP_SIZE_ROWS),
    # Unisex products use the male chart, so both adult genders carry this chart.
    **_charts(BAND_SIZE, (_ADULT_FEMALE, _ADULT_MALE), _BAND_SIZE_ROWS),
    **_charts(WAIST_SIZE, (_ADULT_MALE,), _MENS_WAIST_SIZE_ROWS),
    **_charts(CHEST_SIZE, (_ADULT_MALE,), _MENS_CHEST_SIZE_ROWS),
    # One kids chart each for waist and chest labels. Babies are not sized this way.
    **_charts(WAIST_SIZE, (_CHILD_ALL,), _KIDS_WAIST_SIZE_ROWS),
    **_charts(CHEST_SIZE, (_CHILD_ALL,), _KIDS_CHEST_SIZE_ROWS),
}


def default_scale(
    size_type: SizeType, age_group: AgeGroup | str, gender: Gender | str
) -> ConversionScale:
    """Return the hardcoded chart for this size type and age-group × gender pair.

    Unisex products use the male chart. Children and babies fall back to the
    shared chart for that age group when there is no boys or girls chart.
    """
    age, sex = resolve_age_gender(age_group, gender)
    for candidate in chart_genders(age, sex):
        scale = DEFAULT_SCALES.get((size_type.slug, age, candidate))
        if scale is not None:
            return scale
    tried = " or ".join(
        format_age_gender(age, candidate) for candidate in chart_genders(age, sex)
    )
    raise MissingScaleError(
        f"No default {size_type.label} conversion chart for {tried}. Pass a brand-specific ConversionScale."
    )
