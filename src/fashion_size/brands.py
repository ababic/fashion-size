"""Brands whose size guides this package can convert.

Override charts are JSON files named by id in ``fashion_size/fixtures/charts``.
A brand with no charts matches the default charts. The id, review date, and
source for each override live here. Brands with no garment size system
(homeware, made-to-measure, promotional merch) are omitted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class OverrideChart:
    """One chart that replaces the default for a kind and demographic."""

    id: str
    kind: str
    age_group: str
    gender: str
    guides: tuple[str, ...]
    updated_at: datetime
    source_url: str
    source_notes: str = ""


@dataclass(frozen=True, slots=True)
class Brand:
    """A brand this package can convert.

    ``charts`` lists the guides that differ from the defaults. An empty list
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
                kind="adult-shoe",
                age_group="adult",
                gender="female",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.dunelondon.com/size-guide",
            ),
            OverrideChart(
                id="74ff4e47-b47b-45de-aff2-ee2932013960",
                kind="adult-shoe",
                age_group="adult",
                gender="male",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.dunelondon.com/size-guide",
                source_notes="Official chart lists USA/Canada/Australia in one column; AU values match US (not UK) on this guide.",
            ),
        ),
    ),
    Brand("E.L.V. Denim"),
    Brand(
        "Esska",
        charts=(
            OverrideChart(
                id="b003833b-5930-44dd-8c0a-0795865e02dd",
                kind="adult-shoe",
                age_group="adult",
                gender="female",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://esskashoes.com/pages/esska-size-guide",
                source_notes="EU-primary brand; includes UK 7.5 row.",
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
                kind="adult-shoe",
                age_group="adult",
                gender="male",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://mallet.com/pages/mens-shoes-size-guide",
            ),
            OverrideChart(
                id="33541989-d9c8-4395-87ab-2913ed1e4dec",
                kind="adult-shoe",
                age_group="adult",
                gender="female",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://mallet.com/pages/womens-shoes-size-guide",
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
                kind="adult-shoe",
                age_group="adult",
                gender="male",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.onlytheblind.com/en-us/pages/size-chart",
                source_notes="Mens footwear table; tops use alpha cm guides only.",
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
                kind="adult-shoe",
                age_group="adult",
                gender="female",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://penelopechilvers.com/pages/size-guides",
                source_notes="Footwear conversion with half sizes; AU follows US column.",
            ),
            OverrideChart(
                id="c8292828-b338-44c8-a91a-8a211da44c03",
                kind="adult-shoe",
                age_group="adult",
                gender="male",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://penelopechilvers.com/pages/clothing-size-guides",
                source_notes="Integer UK men's footwear table on clothing size guide; AU follows UK.",
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
                kind="adult-shoe",
                age_group="adult",
                gender="female",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.salt-watersandals.co.uk/products/original-red-womens-sandal",
                source_notes="Salt-Water Original flat-sole women's chart; AU matches US women's sizing per brand.",
            ),
            OverrideChart(
                id="0dd48235-ad6c-40e2-96d7-0dd1c4a47c07",
                kind="kids-shoe",
                age_group="child",
                gender="",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.salt-watersandals.co.uk/products/original-white-kids-sandal",
                source_notes="Salt-Water Original kids/youth chart; EU from official table (midpoint when a range is shown). AU follows UK.",
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
                kind="dress",
                age_group="adult",
                gender="female",
                guides=(
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
                source_url="https://www.urbanoutfitters.com/en-gb/help/size-charts",
                source_notes="UO own-brand women's numeric rows (CM table). Mainline apparel only — not jeans/denim EU. UK 16 uses US 16 per official guide; UK 18/XL also maps to US 16 on the site but is omitted here because the chart requires unique US column values (same US as UK 16).",
            ),
            OverrideChart(
                id="01e55afd-5070-44a4-8b4c-2e6059df053e",
                kind="adult-shoe",
                age_group="adult",
                gender="female",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.urbanoutfitters.com/en-gb/help/size-charts",
                source_notes="UO 'Standard' women's footwear table (not Nike/Vans/Adidas sub-charts).",
            ),
            OverrideChart(
                id="1051f93c-48a5-4cd1-a74f-76faa4328a48",
                kind="adult-shoe",
                age_group="adult",
                gender="male",
                guides=("shoes",),
                updated_at=datetime(2026, 3, 29, tzinfo=UTC),
                source_url="https://www.urbanoutfitters.com/en-gb/help/size-charts",
                source_notes="UO 'Standard' men's footwear table; AU follows UK (chart has no AU column).",
            ),
        ),
    ),
)

SUPPORTED_BRANDS: tuple[str, ...] = tuple(brand.name for brand in BRANDS)
