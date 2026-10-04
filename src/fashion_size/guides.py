"""Product families a brand size guide may cover on its own.

Brands often publish a different chart for one family because a different
supplier cuts that range. A chart names the families it replaces; anything it
does not name keeps the default chart.
"""

from __future__ import annotations

from enum import StrEnum


class OverrideGuide(StrEnum):
    """A family of products that can have its own brand conversion chart."""

    JEANS = "jeans"
    TROUSERS = "trousers"
    SHIRTS = "shirts"
    DRESS_SHIRTS = "dress-shirts"
    SUITS = "suits"
    SUIT_JACKETS = "suit-jackets"
    DRESSES = "dresses"
    UNDERWEAR = "underwear"
    CASUAL_TOPS = "casual-tops"
    KNITWEAR = "knitwear"
    SHOES = "shoes"
    BOOTS = "boots"
    TRAINERS = "trainers"
    ACTIVEWEAR_TOPS = "activewear-tops"
    ACTIVEWEAR_BOTTOMS = "activewear-bottoms"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS: dict[OverrideGuide, str] = {
    OverrideGuide.JEANS: "Jeans",
    OverrideGuide.TROUSERS: "Trousers",
    OverrideGuide.SHIRTS: "Shirts",
    OverrideGuide.DRESS_SHIRTS: "Dress Shirts",
    OverrideGuide.SUITS: "Suits",
    OverrideGuide.SUIT_JACKETS: "Suit Jackets",
    OverrideGuide.DRESSES: "Dresses",
    OverrideGuide.UNDERWEAR: "Underwear",
    OverrideGuide.CASUAL_TOPS: "Casual Tops",
    OverrideGuide.KNITWEAR: "Knitwear",
    OverrideGuide.SHOES: "Shoes",
    OverrideGuide.BOOTS: "Boots",
    OverrideGuide.TRAINERS: "Trainers",
    OverrideGuide.ACTIVEWEAR_TOPS: "Activewear Tops",
    OverrideGuide.ACTIVEWEAR_BOTTOMS: "Activewear Bottoms",
}

OVERRIDE_GUIDES: tuple[OverrideGuide, ...] = tuple(OverrideGuide)
OVERRIDE_GUIDE_SLUGS: frozenset[str] = frozenset(guide.value for guide in OVERRIDE_GUIDES)
