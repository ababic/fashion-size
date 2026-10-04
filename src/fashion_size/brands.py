"""Brands whose size guides this package can convert.

A name is listed when the published guide matches the default charts, or when
``brand_conversion_charts.json`` carries a replacement. Brands with no garment
size system (homeware, made-to-measure, promotional merch) are omitted.
"""

from __future__ import annotations

SUPPORTED_BRANDS: tuple[str, ...] = (
    "Anthropologie",
    "Dune London",
    "E.L.V. Denim",
    "Esska",
    "FatFace",
    "Finisterre",
    "Hush",
    "Jacamo",
    "Janji",
    "Kickers",
    "KILLSTAR",
    "lululemon",
    "Mallet",
    "Manners London",
    "Marks & Spencer",
    "Nobody's Child",
    "Oliver Bonas",
    "Only The Blind",
    "Parlez",
    "Passenger",
    "Penelope Chilvers",
    "Pretty You",
    "Rapanui",
    "Reflo",
    "Reiss",
    "River Island",
    "Salt-Water Sandals",
    "Seasalt Cornwall",
    "Simply Be",
    "Sweaty Betty",
    "TALA",
    "Threadbare",
    "Urban Outfitters",
)
