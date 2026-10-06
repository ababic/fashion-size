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
    SHORTS = "shorts"
    SHIRTS = "shirts"
    DRESS_SHIRTS = "dress-shirts"
    SUITS = "suits"
    SUIT_JACKETS = "suit-jackets"
    DRESSES = "dresses"
    SKIRTS = "skirts"
    UNDERWEAR = "underwear"
    BRAS = "bras"
    SWIMWEAR = "swimwear"
    NIGHTWEAR = "nightwear"
    HOSIERY = "hosiery"
    CASUAL_TOPS = "casual-tops"
    CASUAL_BOTTOMS = "casual-bottoms"
    KNITWEAR = "knitwear"
    OUTERWEAR = "outerwear"
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
    ProductType.SHORTS: "Shorts",
    ProductType.SHIRTS: "Shirts",
    ProductType.DRESS_SHIRTS: "Dress Shirts",
    ProductType.SUITS: "Suits",
    ProductType.SUIT_JACKETS: "Suit Jackets",
    ProductType.DRESSES: "Dresses",
    ProductType.SKIRTS: "Skirts",
    ProductType.UNDERWEAR: "Underwear",
    ProductType.BRAS: "Bras",
    ProductType.SWIMWEAR: "Swimwear",
    ProductType.NIGHTWEAR: "Nightwear",
    ProductType.HOSIERY: "Hosiery",
    ProductType.CASUAL_TOPS: "Casual Tops",
    ProductType.CASUAL_BOTTOMS: "Casual Bottoms",
    ProductType.KNITWEAR: "Knitwear",
    ProductType.OUTERWEAR: "Outerwear",
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


def resolve_product_type(product_type: ProductType | str) -> ProductType:
    """Return the product type for a ``ProductType`` or its slug."""
    if isinstance(product_type, ProductType):
        return product_type
    key = str(product_type).strip().lower()
    try:
        return ProductType(key)
    except ValueError as exc:
        raise ValueError(f"Unknown product type {product_type!r}.") from exc
