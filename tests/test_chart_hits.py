"""chart_hits lists every default chart a token sits on."""

from decimal import Decimal

import pytest

from fashion_size.chart_hits import ChartHits, chart_hits
from fashion_size.demographics import AgeGroup, Gender
from fashion_size.product_types import ProductTypeFamily
from fashion_size.types import Locale

_DRESSES = frozenset({ProductTypeFamily.DRESSES})
_FOOTWEAR = frozenset({ProductTypeFamily.FOOTWEAR})
_BOTTOMS = frozenset({ProductTypeFamily.BOTTOMS})
_TOPS = frozenset({ProductTypeFamily.TOPS})
_BRAS = frozenset({ProductTypeFamily.BRAS})


def _ids(result: ChartHits) -> list[tuple[str, str, str, str, Decimal | None, str, str]]:
    return [
        (
            hit.size_kind,
            "" if hit.chart_region is None else hit.chart_region.value,
            "" if hit.age_group is None else hit.age_group.value,
            "" if hit.gender is None else hit.gender.value,
            hit.number,
            hit.length_token,
            hit.label,
        )
        for hit in result.hits
    ]


def _meet(left: frozenset[object], right: frozenset[object]) -> frozenset[object]:
    """Intersect potentials. An empty set abstains."""
    if not left:
        return right
    if not right:
        return left
    return left & right


def test_length_token_keeps_adult_womens_dress_hits():
    result = chart_hits("14 REG")
    assert _ids(result) == [
        ("dress", "uk", "adult", "female", Decimal(14), "reg", ""),
        ("dress", "us", "adult", "female", Decimal(14), "reg", ""),
        ("dress", "au", "adult", "female", Decimal(14), "reg", ""),
    ]
    assert result.families == _DRESSES
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.FEMALE})
    assert all(hit.families == _DRESSES for hit in result.hits)


@pytest.mark.parametrize(
    ("token", "code"),
    [
        ("SHT", "sht"),
        ("REG", "reg"),
        ("LNG", "lng"),
        ("PET", "pet"),
        ("TAL", "tal"),
        ("S", "s"),
        ("R", "r"),
        ("L", "l"),
        ("T", "t"),
    ],
)
def test_each_length_token(token: str, code: str):
    result = chart_hits(f"14 {token}")
    assert [hit.length_token for hit in result.hits] == [code, code, code]
    assert [(hit.chart_region, hit.number) for hit in result.hits] == [
        (Locale.UK, Decimal(14)),
        (Locale.US, Decimal(14)),
        (Locale.AU, Decimal(14)),
    ]


def test_region_prefix_keeps_that_regions_shoe_charts():
    result = chart_hits("EU 39")
    assert _ids(result) == [
        ("adult-shoe", "eu", "adult", "female", Decimal(39), "", ""),
        ("adult-shoe", "eu", "adult", "male", Decimal(39), "", ""),
    ]
    assert result.families == _FOOTWEAR
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.FEMALE, Gender.MALE})
    assert chart_hits("eu-39").hits == result.hits
    assert chart_hits("EUR 39").hits == result.hits


def test_bare_number_adds_mens_waist_and_chest_beside_the_eu_shoes():
    result = chart_hits("39")
    assert _ids(result) == [
        ("waist-size", "uk", "adult", "male", Decimal(39), "", ""),
        ("waist-size", "us", "adult", "male", Decimal(39), "", ""),
        ("waist-size", "au", "adult", "male", Decimal(39), "", ""),
        ("chest-size", "uk", "adult", "male", Decimal(39), "", ""),
        ("chest-size", "us", "adult", "male", Decimal(39), "", ""),
        ("chest-size", "au", "adult", "male", Decimal(39), "", ""),
        ("adult-shoe", "eu", "adult", "female", Decimal(39), "", ""),
        ("adult-shoe", "eu", "adult", "male", Decimal(39), "", ""),
    ]
    assert result.families == _FOOTWEAR | _BOTTOMS | _TOPS
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.FEMALE, Gender.MALE})
    assert not any(
        hit.size_kind == "adult-shoe" and hit.chart_region is Locale.UK
        for hit in result.hits
    )


def test_bare_eight_lists_every_chart_that_contains_it():
    # US 8 and AU 8 are on the women's shoe chart (the UK 6 row), so those
    # columns are hits as well as UK 8.
    result = chart_hits("8")
    assert _ids(result) == [
        ("dress", "uk", "adult", "female", Decimal(8), "", ""),
        ("dress", "us", "adult", "female", Decimal(8), "", ""),
        ("dress", "au", "adult", "female", Decimal(8), "", ""),
        ("dress", "uk", "child", "", Decimal(8), "", ""),
        ("dress", "us", "child", "", Decimal(8), "", ""),
        ("dress", "au", "child", "", Decimal(8), "", ""),
        ("adult-shoe", "uk", "adult", "female", Decimal(8), "", ""),
        ("adult-shoe", "us", "adult", "female", Decimal(8), "", ""),
        ("adult-shoe", "au", "adult", "female", Decimal(8), "", ""),
        ("adult-shoe", "uk", "adult", "male", Decimal(8), "", ""),
        ("adult-shoe", "us", "adult", "male", Decimal(8), "", ""),
        ("adult-shoe", "au", "adult", "male", Decimal(8), "", ""),
        ("kids-shoe", "uk", "child", "", Decimal(8), "", ""),
        ("kids-shoe", "us", "child", "", Decimal(8), "", ""),
        ("kids-shoe", "au", "child", "", Decimal(8), "", ""),
        ("band-size", "au", "adult", "", Decimal(8), "", ""),
    ]
    assert result.families == _DRESSES | _FOOTWEAR | _BRAS
    assert result.age_groups == frozenset({AgeGroup.ADULT, AgeGroup.CHILD})
    assert result.genders == frozenset({Gender.FEMALE, Gender.MALE})
    band = next(hit for hit in result.hits if hit.size_kind == "band-size")
    assert band.families == _BRAS
    assert band.gender is None
    assert all(hit.gender is not Gender.UNISEX for hit in result.hits)


def test_length_token_on_eight_drops_shoes_band_and_child_hits():
    result = chart_hits("8 REG")
    assert _ids(result) == [
        ("dress", "uk", "adult", "female", Decimal(8), "reg", ""),
        ("dress", "us", "adult", "female", Decimal(8), "reg", ""),
        ("dress", "au", "adult", "female", Decimal(8), "reg", ""),
    ]
    assert result.families == _DRESSES
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.FEMALE})


def test_two_tokens_intersect_to_adult_womens_dresses():
    eight = chart_hits("8")
    regular = chart_hits("14 REG")
    assert _meet(eight.families, regular.families) == _DRESSES
    assert _meet(eight.age_groups, regular.age_groups) == frozenset({AgeGroup.ADULT})
    assert _meet(eight.genders, regular.genders) == frozenset({Gender.FEMALE})


def test_slash_length_keeps_eu_dress_waist_and_chest():
    result = chart_hits("58/60L")
    expected = []
    for number in (58, 60):
        expected.extend(
            [
                ("dress", "eu", "adult", "female", Decimal(number), "l", ""),
                ("dress", "eu", "adult", "male", Decimal(number), "l", ""),
                ("waist-size", "eu", "adult", "male", Decimal(number), "l", ""),
                ("chest-size", "eu", "adult", "male", Decimal(number), "l", ""),
            ]
        )
    assert _ids(result) == expected
    assert result.families == _DRESSES | _BOTTOMS | _TOPS
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.FEMALE, Gender.MALE})
    assert not any(
        hit.chart_region is Locale.UK and hit.size_kind == "waist-size"
        for hit in result.hits
    )


def test_sixty_two_with_a_length_is_eu_waist_and_chest():
    result = chart_hits("62L")
    assert _ids(result) == [
        ("waist-size", "eu", "adult", "male", Decimal(62), "l", ""),
        ("chest-size", "eu", "adult", "male", Decimal(62), "l", ""),
    ]
    assert result.families == _BOTTOMS | _TOPS
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.MALE})


def test_cup_range_beside_a_bra_dress_number_is_uk_dress_and_bras():
    result = chart_hits("10 A-C")
    assert _ids(result) == [
        ("dress", "uk", "adult", "female", Decimal(10), "", ""),
        ("cup-range", "", "", "", None, "", "A-C"),
    ]
    assert all(hit.families == _BRAS for hit in result.hits)
    assert result.families == _BRAS
    assert result.age_groups == frozenset({AgeGroup.ADULT})
    assert result.genders == frozenset({Gender.FEMALE})
    assert chart_hits("10A–C").hits == result.hits
    # The bra dress label stays UK even when another region is written first.
    assert chart_hits("US 10 A-C").hits == result.hits


@pytest.mark.parametrize("span", ["A-C", "D-E", "F-G", "GG-H"])
def test_cup_range_alone_is_bras_and_abstains_on_age_and_gender(span: str):
    result = chart_hits(span)
    assert _ids(result) == [("cup-range", "", "", "", None, "", span)]
    assert result.families == _BRAS
    assert result.age_groups == frozenset()
    assert result.genders == frozenset()


def test_cup_letter_is_a_band_and_drops_the_dress_hit():
    for raw in ("30C", "32C"):
        result = chart_hits(raw)
        number = Decimal(raw[:2])
        assert _ids(result) == [
            ("band-size", "uk", "adult", "", number, "", ""),
            ("band-size", "us", "adult", "", number, "", ""),
            ("band-size", "au", "adult", "", number, "", ""),
            ("cup-size", "", "adult", "female", None, "", "C"),
        ]
        assert all(hit.families == _BRAS for hit in result.hits)
        assert result.families == _BRAS
        assert result.age_groups == frozenset({AgeGroup.ADULT})
        assert result.genders == frozenset({Gender.FEMALE})
        assert not any(hit.size_kind == "dress" for hit in result.hits)


def test_cup_letter_uses_only_the_prefixed_band_region():
    result = chart_hits("UK 32C")
    assert [hit.chart_region for hit in result.hits if hit.size_kind == "band-size"] == [
        Locale.UK
    ]
    assert result.hits[-1].size_kind == "cup-size"
    assert result.hits[-1].label == "C"


def test_eight_c_is_the_au_band_not_the_dress():
    result = chart_hits("8C")
    assert _ids(result) == [
        ("band-size", "au", "adult", "", Decimal(8), "", ""),
        ("cup-size", "", "adult", "female", None, "", "C"),
    ]
    assert result.families == _BRAS
    ranged = chart_hits("8 A-C")
    assert [hit.size_kind for hit in ranged.hits] == ["dress", "cup-range"]
    assert ranged.hits[0].chart_region is Locale.UK
    assert ranged.hits[0].families == _BRAS


@pytest.mark.parametrize(
    ("raw", "label"),
    [
        ("S", "S"),
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("small", "S"),
        ("medium", "M"),
        ("XXL", "2XL"),
        ("one size", "ONE"),
    ],
)
def test_letter_abstains(raw: str, label: str):
    result = chart_hits(raw)
    assert _ids(result) == [("letter", "", "", "", None, "", label)]
    assert result.families == frozenset()
    assert result.age_groups == frozenset()
    assert result.genders == frozenset()
    eight = chart_hits("8")
    assert _meet(result.families, eight.families) == eight.families
    assert _meet(result.age_groups, eight.age_groups) == eight.age_groups
    assert _meet(result.genders, eight.genders) == eight.genders


@pytest.mark.parametrize(
    ("raw", "kind", "label", "age"),
    [
        ("2-3 years", "age-years", "2-3", AgeGroup.CHILD),
        ("5-6 yrs", "age-years", "5-6", AgeGroup.CHILD),
        ("6 months", "age-months", "6", AgeGroup.BABY),
        ("6 mths", "age-months", "6", AgeGroup.BABY),
    ],
)
def test_age_label_sets_only_its_age_group(
    raw: str, kind: str, label: str, age: AgeGroup
):
    result = chart_hits(raw)
    assert _ids(result) == [(kind, "", age.value, "", None, "", label)]
    assert result.families == frozenset()
    assert result.genders == frozenset()
    assert result.age_groups == frozenset({age})
    assert all(hit.families == frozenset() for hit in result.hits)


def test_age_label_narrows_a_shoe_that_is_also_a_child_size():
    months = chart_hits("6 months")
    years = chart_hits("2-3 years")
    one = chart_hits("1")
    assert _meet(months.age_groups, one.age_groups) == frozenset({AgeGroup.BABY})
    assert _meet(years.age_groups, one.age_groups) == frozenset({AgeGroup.CHILD})
    assert _meet(months.families, one.families) == _FOOTWEAR


def test_number_on_no_chart_is_unplaced_and_abstains():
    result = chart_hits("99")
    assert _ids(result) == [("unplaced", "", "", "", Decimal(99), "", "")]
    assert result.families == frozenset()
    assert result.age_groups == frozenset()
    assert result.genders == frozenset()
    marked = chart_hits("99 REG")
    assert _ids(marked) == [("unplaced", "", "", "", Decimal(99), "reg", "")]
    assert marked.families == marked.age_groups == marked.genders == frozenset()


def test_length_token_that_drops_every_chart_abstains():
    result = chart_hits("3 REG")
    assert result.hits == ()
    assert result.families == result.age_groups == result.genders == frozenset()


def test_kids_shoe_span_is_returned_once_as_child():
    result = chart_hits("1")
    assert any(
        hit.size_kind == "baby-shoe" and hit.age_group is AgeGroup.BABY
        for hit in result.hits
    )
    assert any(
        hit.size_kind == "kids-shoe" and hit.age_group is AgeGroup.CHILD
        for hit in result.hits
    )
    assert not any(
        hit.size_kind == "kids-shoe" and hit.age_group is AgeGroup.BABY
        for hit in result.hits
    )
    assert not any(hit.size_kind == "adult-shoe" for hit in result.hits)
    assert result.age_groups == frozenset({AgeGroup.BABY, AgeGroup.CHILD})
    assert result.genders == frozenset()
    assert result.families == _FOOTWEAR


def test_adult_chart_is_returned_with_the_baby_and_child_shoes():
    result = chart_hits("5")
    assert any(
        hit.size_kind == "baby-shoe" and hit.age_group is AgeGroup.BABY
        for hit in result.hits
    )
    assert any(
        hit.size_kind == "kids-shoe" and hit.age_group is AgeGroup.CHILD
        for hit in result.hits
    )
    assert any(
        hit.size_kind == "adult-shoe"
        and hit.age_group is AgeGroup.ADULT
        and hit.gender is Gender.FEMALE
        for hit in result.hits
    )
    assert not any(hit.age_group is AgeGroup.BABY and hit.size_kind == "kids-shoe" for hit in result.hits)


def test_prefixed_baby_and_child_shoe_spans_stay_apart():
    baby = chart_hits("EU 16")
    assert [(hit.size_kind, hit.age_group) for hit in baby.hits] == [
        ("baby-shoe", AgeGroup.BABY)
    ]
    child = chart_hits("EU 23")
    assert [(hit.size_kind, hit.age_group) for hit in child.hits] == [
        ("kids-shoe", AgeGroup.CHILD)
    ]


def test_french_prefix_uses_eu_numbers_and_skips_waist():
    french = chart_hits("FR 46")
    european = chart_hits("EU 46")
    assert french.hits
    assert all(hit.chart_region is Locale.FR for hit in french.hits)
    assert any(hit.size_kind == "waist-size" for hit in european.hits)
    assert not any(hit.size_kind == "waist-size" for hit in french.hits)
    assert {hit.size_kind for hit in french.hits} == {
        "dress",
        "chest-size",
        "adult-shoe",
    }
    assert chart_hits("FR 90").hits[0].size_kind == "band-size"
    assert chart_hits("FR 90").hits[0].chart_region is Locale.FR
    assert chart_hits("FR 90").families == _BRAS


def test_region_prefix_limits_a_bare_chart_number():
    result = chart_hits("UK 8")
    assert result.hits
    assert all(hit.chart_region is Locale.UK for hit in result.hits)
    assert not any(hit.size_kind == "band-size" for hit in result.hits)


def test_whitespace_is_collapsed():
    assert chart_hits("  14   REG  ").hits == chart_hits("14 REG").hits
    assert chart_hits("14 reg").hits == chart_hits("14 REG").hits
    assert chart_hits("58 / 60 L").hits == chart_hits("58/60L").hits


def test_empty_and_unrecognised_tokens_have_no_hits():
    for raw in ("", "   ", "not-a-size", "REG", "14X"):
        result = chart_hits(raw)
        assert result.hits == ()
        assert result.families == result.age_groups == result.genders == frozenset()


def test_token_must_be_a_string():
    with pytest.raises(TypeError, match="token must be a str"):
        chart_hits(None)  # type: ignore[arg-type]
