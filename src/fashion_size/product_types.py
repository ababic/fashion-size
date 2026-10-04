"""Product types a brand size guide may cover on its own.

Brands often publish a different chart for one product type because a different
supplier cuts that range. A chart names the product types it replaces; anything
it does not name keeps the default chart.
"""

from __future__ import annotations

from enum import StrEnum


class ProductType(StrEnum):
    """A product range that can have its own brand conversion chart."""

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


_LABELS: dict[ProductType, str] = {
    ProductType.JEANS: "Jeans",
    ProductType.TROUSERS: "Trousers",
    ProductType.SHIRTS: "Shirts",
    ProductType.DRESS_SHIRTS: "Dress Shirts",
    ProductType.SUITS: "Suits",
    ProductType.SUIT_JACKETS: "Suit Jackets",
    ProductType.DRESSES: "Dresses",
    ProductType.UNDERWEAR: "Underwear",
    ProductType.CASUAL_TOPS: "Casual Tops",
    ProductType.KNITWEAR: "Knitwear",
    ProductType.SHOES: "Shoes",
    ProductType.BOOTS: "Boots",
    ProductType.TRAINERS: "Trainers",
    ProductType.ACTIVEWEAR_TOPS: "Activewear Tops",
    ProductType.ACTIVEWEAR_BOTTOMS: "Activewear Bottoms",
}

PRODUCT_TYPES: tuple[ProductType, ...] = tuple(ProductType)
PRODUCT_TYPE_SLUGS: frozenset[str] = frozenset(
    product_type.value for product_type in PRODUCT_TYPES
)
