"""Age group and gender values used to pick a conversion chart.

These match the warehouse catalogue pair (``adult`` / ``child`` / ``baby`` with
``male`` / ``female`` / ``unisex``) without importing that project's models.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AgeGroup(StrEnum):
    """Who the chart is for."""

    ADULT = "adult"
    CHILD = "child"
    BABY = "baby"

    @property
    def label(self) -> str:
        return _AGE_GROUP_LABELS[self]


class Gender(StrEnum):
    """Which chart within an age group.

    There is no unisex chart. A unisex product uses the male chart.
    """

    UNISEX = "unisex"
    MALE = "male"
    FEMALE = "female"

    @property
    def label(self) -> str:
        return _GENDER_LABELS[self]


_AGE_GROUP_LABELS: dict[AgeGroup, str] = {
    AgeGroup.ADULT: "Adults",
    AgeGroup.CHILD: "Children",
    AgeGroup.BABY: "Babies",
}
_GENDER_LABELS: dict[Gender, str] = {
    Gender.UNISEX: "Unisex",
    Gender.MALE: "Male",
    Gender.FEMALE: "Female",
}

# Display names for the usual nine age × gender slots.
DEMOGRAPHIC_LABELS: dict[tuple[str, str], str] = {
    ("adult", "male"): "Men",
    ("adult", "female"): "Women",
    ("adult", "unisex"): "Unisex Adults",
    ("child", "male"): "Boys",
    ("child", "female"): "Girls",
    ("child", "unisex"): "Unisex Kids",
    ("baby", "male"): "Baby Boys",
    ("baby", "female"): "Baby Girls",
    ("baby", "unisex"): "Unisex Baby",
}


def age_group_label(age_group: str) -> str:
    return AgeGroup(age_group).label


def gender_label(gender: str) -> str:
    return Gender(gender).label


@dataclass(frozen=True, slots=True)
class Demographic:
    """Age group and gender pair used to pick a conversion chart."""

    age_group: AgeGroup | str
    gender: Gender | str

    def as_chart_pair(self) -> tuple[str, str]:
        """Return normalised ``(age_group, gender)`` strings for chart lookup."""
        age = (
            self.age_group.value
            if isinstance(self.age_group, AgeGroup)
            else str(self.age_group or "").strip().lower()
        )
        sex = (
            self.gender.value
            if isinstance(self.gender, Gender)
            else str(self.gender or "").strip().lower()
        )
        if age not in AgeGroup:
            raise ValueError(f"Unknown age group {self.age_group!r}.")
        if sex not in Gender:
            raise ValueError(f"Unknown gender {self.gender!r}.")
        return age, sex
