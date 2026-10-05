"""Brands whose size guides this package can convert.

Override charts are JSON files named by id in ``fashion_size/fixtures/charts``.
Each file holds the rows, the source page, and notes about that table. A brand
with no charts matches the default charts. The id, size type, demographic,
product types, and review date for each override live here. Brands with no
garment size system (homeware, made-to-measure, promotional merch) are omitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from fashion_size.product_types import ProductType


class BrandName(StrEnum):
    """Catalog brand name. The value is the spelling used on charts."""

    ANTHROPOLOGIE = "Anthropologie"
    DUNE_LONDON = "Dune London"
    ELV_DENIM = "E.L.V. Denim"
    ESSKA = "Esska"
    FATFACE = "FatFace"
    FINISTERRE = "Finisterre"
    HUSH = "Hush"
    JACAMO = "Jacamo"
    JANJI = "Janji"
    KICKERS = "Kickers"
    KILLSTAR = "KILLSTAR"
    LULULEMON = "lululemon"
    MALLET = "Mallet"
    MANNERS_LONDON = "Manners London"
    MARKS_AND_SPENCER = "Marks & Spencer"
    NOBODYS_CHILD = "Nobody's Child"
    OLIVER_BONAS = "Oliver Bonas"
    ONLY_THE_BLIND = "Only The Blind"
    PARLEZ = "Parlez"
    PASSENGER = "Passenger"
    PENELOPE_CHILVERS = "Penelope Chilvers"
    PRETTY_YOU = "Pretty You"
    RAPANUI = "Rapanui"
    REFLO = "Reflo"
    REISS = "Reiss"
    RIVER_ISLAND = "River Island"
    SALT_WATER_SANDALS = "Salt-Water Sandals"
    SEASALT_CORNWALL = "Seasalt Cornwall"
    SIMPLY_BE = "Simply Be"
    SWEATY_BETTY = "Sweaty Betty"
    TALA = "TALA"
    THREADBARE = "Threadbare"
    URBAN_OUTFITTERS = "Urban Outfitters"


@dataclass(frozen=True, slots=True)
class OverrideChart:
    """One chart that replaces the default for a size type and demographic."""

    id: str
    size_type: str
    age_group: str
    gender: str
    product_types: tuple[ProductType, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Brand:
    """A brand this package can convert.

    ``charts`` lists the size guides that differ from the defaults. An empty list
    means the published guide was accepted as the default charts.
    """

    name: BrandName
    charts: tuple[OverrideChart, ...] = ()

    @property
    def differs_from_default(self) -> bool:
        """Whether any shipped chart replaces the default for this brand."""
        return bool(self.charts)


BRANDS: tuple[Brand, ...] = (
    Brand(BrandName.ANTHROPOLOGIE),
    Brand(
        BrandName.DUNE_LONDON,
        charts=(
            OverrideChart(
                id="986c0c43-fe4d-4741-af34-99e522e607c4",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="74ff4e47-b47b-45de-aff2-ee2932013960",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand(BrandName.ELV_DENIM),
    Brand(
        BrandName.ESSKA,
        charts=(
            OverrideChart(
                id="b003833b-5930-44dd-8c0a-0795865e02dd",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand(BrandName.FATFACE),
    Brand(BrandName.FINISTERRE),
    Brand(BrandName.HUSH),
    Brand(BrandName.JACAMO),
    Brand(BrandName.JANJI),
    Brand(BrandName.KICKERS),
    Brand(BrandName.KILLSTAR),
    Brand(BrandName.LULULEMON),
    Brand(
        BrandName.MALLET,
        charts=(
            OverrideChart(
                id="b93a2493-220b-4a6f-aa43-eea55506dfe7",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="33541989-d9c8-4395-87ab-2913ed1e4dec",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand(BrandName.MANNERS_LONDON),
    Brand(BrandName.MARKS_AND_SPENCER),
    Brand(BrandName.NOBODYS_CHILD),
    Brand(BrandName.OLIVER_BONAS),
    Brand(
        BrandName.ONLY_THE_BLIND,
        charts=(
            OverrideChart(
                id="d01ea2f4-1000-43b6-86ba-905c44bd2236",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand(BrandName.PARLEZ),
    Brand(BrandName.PASSENGER),
    Brand(
        BrandName.PENELOPE_CHILVERS,
        charts=(
            OverrideChart(
                id="dcdef7f9-de9d-4238-a045-1f9ef8157107",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="c8292828-b338-44c8-a91a-8a211da44c03",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand(BrandName.PRETTY_YOU),
    Brand(BrandName.RAPANUI),
    Brand(BrandName.REFLO),
    Brand(BrandName.REISS),
    Brand(BrandName.RIVER_ISLAND),
    Brand(
        BrandName.SALT_WATER_SANDALS,
        charts=(
            OverrideChart(
                id="a76bff9f-21af-4745-9b5a-014b8fa6e805",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="0dd48235-ad6c-40e2-96d7-0dd1c4a47c07",
                size_type="kids-shoe",
                age_group="child",
                gender="",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand(BrandName.SEASALT_CORNWALL),
    Brand(BrandName.SIMPLY_BE),
    Brand(BrandName.SWEATY_BETTY),
    Brand(BrandName.TALA),
    Brand(BrandName.THREADBARE),
    Brand(
        BrandName.URBAN_OUTFITTERS,
        charts=(
            OverrideChart(
                id="2df783be-e0c8-46b7-8ae5-60924def56d5",
                size_type="dress",
                age_group="adult",
                gender="female",
                product_types=(
                    ProductType.TROUSERS,
                    ProductType.SHIRTS,
                    ProductType.DRESS_SHIRTS,
                    ProductType.SUITS,
                    ProductType.SUIT_JACKETS,
                    ProductType.DRESSES,
                    ProductType.UNDERWEAR,
                    ProductType.CASUAL_TOPS,
                    ProductType.KNITWEAR,
                    ProductType.ACTIVEWEAR_TOPS,
                    ProductType.ACTIVEWEAR_BOTTOMS,
                ),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="01e55afd-5070-44a4-8b4c-2e6059df053e",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="1051f93c-48a5-4cd1-a74f-76faa4328a48",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=(ProductType.SHOES,),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
)

SUPPORTED_BRANDS: tuple[BrandName, ...] = tuple(brand.name for brand in BRANDS)


def brand_differs_from_default(name: BrandName) -> bool:
    """Whether the catalog lists any override chart for ``name``."""
    for brand in BRANDS:
        if brand.name == name:
            return brand.differs_from_default
    raise ValueError(f"Unknown brand {name!r}.")


def resolve_brand_name(name: BrandName | str) -> BrandName | None:
    """Return the catalog ``BrandName`` for ``name``, or ``None`` when it is not listed.

    Matching ignores case and surrounding whitespace. A name that is not in the
    catalog is not an error: conversion uses the default chart.
    """
    if isinstance(name, BrandName):
        return name
    key = name.strip().casefold()
    if not key:
        return None
    for brand in BrandName:
        if brand.casefold() == key:
            return brand
    return None
