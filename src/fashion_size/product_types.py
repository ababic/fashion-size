"""Product types a brand size guide may cover on its own.

Brands often publish a different chart for one product type because a different
supplier cuts that range. A chart names the product types it replaces; anything
it does not name keeps the default chart.

Product types that share a way of reading a feed size string belong to one
``ProductTypeFamily``. A jeans waist and a trouser waist are the same kind of
number. A dress size and a skirt size are too. Each product type also carries
a ``ProductTypeProfile`` for the cases that are not shared: a suit number in
the jacket range is a chest size, and a dress shirt can pair a collar with a
sleeve.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProductTypeFamily(StrEnum):
    """Product ranges that share how an unlabelled size string is read."""

    BOTTOMS = "bottoms"
    TOPS = "tops"
    FOOTWEAR = "footwear"
    DRESSES = "dresses"
    BRAS = "bras"
    OTHER = "other"

    @property
    def label(self) -> str:
        return _FAMILY_LABELS[self]

    @property
    def product_types(self) -> tuple[ProductType, ...]:
        """Product types that belong to this family, in enum order."""
        return tuple(product for product in ProductType if product.family is self)

    @property
    def bare_waist_span(self) -> tuple[int, int] | None:
        """Inclusive inch or centimetre waist read from a bare number, if any."""
        if self is ProductTypeFamily.BOTTOMS:
            return (24, 44)
        return None

    @property
    def chart_waist_span(self) -> tuple[int, int] | None:
        """Inclusive waist-size chart label read from a number, if any."""
        if self is ProductTypeFamily.BOTTOMS:
            return (24, 50)
        return None

    @property
    def accepts_fit_code(self) -> bool:
        """``16T`` and ``8R`` are a size plus a proportion on these families."""
        return self in {ProductTypeFamily.DRESSES, ProductTypeFamily.TOPS}

    @property
    def reads_shoe_size(self) -> bool:
        return self is ProductTypeFamily.FOOTWEAR

    @property
    def reads_dress_size(self) -> bool:
        return self is ProductTypeFamily.DRESSES


_FAMILY_LABELS: dict[ProductTypeFamily, str] = {
    ProductTypeFamily.BOTTOMS: "Bottoms",
    ProductTypeFamily.TOPS: "Tops",
    ProductTypeFamily.FOOTWEAR: "Footwear",
    ProductTypeFamily.DRESSES: "Dresses",
    ProductTypeFamily.BRAS: "Bras",
    ProductTypeFamily.OTHER: "Other",
}


class ProductType(StrEnum):
    """A product range that can have its own brand conversion chart."""

    JEANS = "jeans"
    TROUSERS = "trousers"
    SHORTS = "shorts"
    SHIRTS = "shirts"
    DRESS_SHIRTS = "dress-shirts"
    SUITS = "suits"
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

    @property
    def profile(self) -> ProductTypeProfile:
        """Family, plus collar and chest spans that belong to this product type."""
        return _PROFILES[self]

    @property
    def family(self) -> ProductTypeFamily:
        return self.profile.family

    @property
    def takes_letter_size(self) -> bool:
        """Whether a generic S/M/L on this product is a letter size.

        Bras keep those letters as cup sizes. Footwear uses a shoe size.
        Activewear bottoms are not in the letter-size set.
        """
        if self.family in {
            ProductTypeFamily.BOTTOMS,
            ProductTypeFamily.TOPS,
            ProductTypeFamily.DRESSES,
        }:
            return True
        return self in {ProductType.UNDERWEAR, ProductType.HOSIERY}


_LABELS: dict[ProductType, str] = {
    ProductType.JEANS: "Jeans",
    ProductType.TROUSERS: "Trousers",
    ProductType.SHORTS: "Shorts",
    ProductType.SHIRTS: "Shirts",
    ProductType.DRESS_SHIRTS: "Dress Shirts",
    ProductType.SUITS: "Suits & Tailoring",
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


@dataclass(frozen=True, slots=True)
class ProductTypeProfile:
    """Configuration a product type owns for reading a feed size string.

    ``chest_span`` is the inclusive jacket range read as a chest size
    (outerwear and suits). ``collar_span`` is the inclusive range of a bare
    dress-shirt number read as a collar. ``collar_sleeve`` is
    ``(collar low, collar high, sleeve low, sleeve high)`` for a ``15.5/34``
    cell.
    """

    family: ProductTypeFamily
    chest_span: tuple[int, int] | None = None
    collar_span: tuple[int, int] | None = None
    collar_sleeve: tuple[int, int, int, int] | None = None


_PROFILES: dict[ProductType, ProductTypeProfile] = {
    ProductType.JEANS: ProductTypeProfile(ProductTypeFamily.BOTTOMS),
    ProductType.TROUSERS: ProductTypeProfile(ProductTypeFamily.BOTTOMS),
    ProductType.SHORTS: ProductTypeProfile(ProductTypeFamily.BOTTOMS),
    ProductType.CASUAL_BOTTOMS: ProductTypeProfile(ProductTypeFamily.BOTTOMS),
    ProductType.SUITS: ProductTypeProfile(
        ProductTypeFamily.BOTTOMS, chest_span=(34, 60)
    ),
    ProductType.SHIRTS: ProductTypeProfile(
        ProductTypeFamily.TOPS, collar_sleeve=(14, 22, 28, 40)
    ),
    ProductType.DRESS_SHIRTS: ProductTypeProfile(
        ProductTypeFamily.TOPS,
        collar_span=(14, 22),
        collar_sleeve=(14, 22, 28, 40),
    ),
    ProductType.CASUAL_TOPS: ProductTypeProfile(ProductTypeFamily.TOPS),
    ProductType.KNITWEAR: ProductTypeProfile(ProductTypeFamily.TOPS),
    ProductType.OUTERWEAR: ProductTypeProfile(
        ProductTypeFamily.TOPS, chest_span=(34, 60)
    ),
    ProductType.ACTIVEWEAR_TOPS: ProductTypeProfile(ProductTypeFamily.TOPS),
    ProductType.DRESSES: ProductTypeProfile(ProductTypeFamily.DRESSES),
    ProductType.SKIRTS: ProductTypeProfile(ProductTypeFamily.DRESSES),
    ProductType.NIGHTWEAR: ProductTypeProfile(ProductTypeFamily.DRESSES),
    ProductType.SWIMWEAR: ProductTypeProfile(ProductTypeFamily.DRESSES),
    ProductType.BRAS: ProductTypeProfile(ProductTypeFamily.BRAS),
    ProductType.UNDERWEAR: ProductTypeProfile(ProductTypeFamily.OTHER),
    ProductType.HOSIERY: ProductTypeProfile(ProductTypeFamily.OTHER),
    ProductType.ACTIVEWEAR_BOTTOMS: ProductTypeProfile(ProductTypeFamily.OTHER),
    ProductType.SHOES: ProductTypeProfile(ProductTypeFamily.FOOTWEAR),
    ProductType.BOOTS: ProductTypeProfile(ProductTypeFamily.FOOTWEAR),
    ProductType.TRAINERS: ProductTypeProfile(ProductTypeFamily.FOOTWEAR),
}

_MISSING_PROFILES = [
    product.value for product in ProductType if product not in _PROFILES
]
if _MISSING_PROFILES:
    raise RuntimeError(
        "Product types without a profile: " + ", ".join(_MISSING_PROFILES)
    )


PRODUCT_TYPES: tuple[ProductType, ...] = tuple(ProductType)
PRODUCT_TYPE_FAMILIES: tuple[ProductTypeFamily, ...] = tuple(ProductTypeFamily)
PRODUCT_TYPE_SLUGS: frozenset[str] = frozenset(
    product_type.value for product_type in PRODUCT_TYPES
)
_ALIASES: dict[str, ProductType] = {
    "suit-jackets": ProductType.SUITS,
}


def resolve_product_type(product_type: ProductType | str) -> ProductType:
    """Return the product type for a ``ProductType`` or its slug."""
    if isinstance(product_type, ProductType):
        return product_type
    key = str(product_type).strip().lower()
    if key in _ALIASES:
        return _ALIASES[key]
    try:
        return ProductType(key)
    except ValueError as exc:
        raise ValueError(f"Unknown product type {product_type!r}.") from exc
