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


@dataclass(frozen=True, slots=True)
class OverrideChart:
    """One chart that replaces the default for a size type and demographic."""

    id: str
    size_type: str
    age_group: str
    gender: str
    product_types: tuple[str, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Brand:
    """A brand this package can convert.

    ``charts`` lists the size guides that differ from the defaults. An empty list
    means the published guide was accepted as the default charts.
    """

    name: str
    charts: tuple[OverrideChart, ...] = ()

    @property
    def differs_from_default(self) -> bool:
        """Whether any shipped chart replaces the default for this brand."""
        return bool(self.charts)


BRANDS: tuple[Brand, ...] = (
    Brand("Anthropologie"),
    Brand(
        "Dune London",
        charts=(
            OverrideChart(
                id="986c0c43-fe4d-4741-af34-99e522e607c4",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="74ff4e47-b47b-45de-aff2-ee2932013960",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand("E.L.V. Denim"),
    Brand(
        "Esska",
        charts=(
            OverrideChart(
                id="b003833b-5930-44dd-8c0a-0795865e02dd",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand("FatFace"),
    Brand("Finisterre"),
    Brand("Hush"),
    Brand("Jacamo"),
    Brand("Janji"),
    Brand("Kickers"),
    Brand("KILLSTAR"),
    Brand("lululemon"),
    Brand(
        "Mallet",
        charts=(
            OverrideChart(
                id="b93a2493-220b-4a6f-aa43-eea55506dfe7",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="33541989-d9c8-4395-87ab-2913ed1e4dec",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand("Manners London"),
    Brand("Marks & Spencer"),
    Brand("Nobody's Child"),
    Brand("Oliver Bonas"),
    Brand(
        "Only The Blind",
        charts=(
            OverrideChart(
                id="d01ea2f4-1000-43b6-86ba-905c44bd2236",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand("Parlez"),
    Brand("Passenger"),
    Brand(
        "Penelope Chilvers",
        charts=(
            OverrideChart(
                id="dcdef7f9-de9d-4238-a045-1f9ef8157107",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="c8292828-b338-44c8-a91a-8a211da44c03",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand("Pretty You"),
    Brand("Rapanui"),
    Brand("Reflo"),
    Brand("Reiss"),
    Brand("River Island"),
    Brand(
        "Salt-Water Sandals",
        charts=(
            OverrideChart(
                id="a76bff9f-21af-4745-9b5a-014b8fa6e805",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="0dd48235-ad6c-40e2-96d7-0dd1c4a47c07",
                size_type="kids-shoe",
                age_group="child",
                gender="",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
    Brand("Seasalt Cornwall"),
    Brand("Simply Be"),
    Brand("Sweaty Betty"),
    Brand("TALA"),
    Brand("Threadbare"),
    Brand(
        "Urban Outfitters",
        charts=(
            OverrideChart(
                id="2df783be-e0c8-46b7-8ae5-60924def56d5",
                size_type="dress",
                age_group="adult",
                gender="female",
                product_types=(
                    "trousers",
                    "shirts",
                    "dress-shirts",
                    "suits",
                    "suit-jackets",
                    "dresses",
                    "underwear",
                    "casual-tops",
                    "knitwear",
                    "activewear-tops",
                    "activewear-bottoms",
                ),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="01e55afd-5070-44a4-8b4c-2e6059df053e",
                size_type="adult-shoe",
                age_group="adult",
                gender="female",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
            OverrideChart(
                id="1051f93c-48a5-4cd1-a74f-76faa4328a48",
                size_type="adult-shoe",
                age_group="adult",
                gender="male",
                product_types=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
            ),
        ),
    ),
)

SUPPORTED_BRANDS: tuple[str, ...] = tuple(brand.name for brand in BRANDS)
