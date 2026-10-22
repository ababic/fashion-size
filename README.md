# fashion-size

[![PyPI version](https://img.shields.io/pypi/v/fashion-size.svg)](https://pypi.org/project/fashion-size/)
[![Python versions](https://img.shields.io/pypi/pyversions/fashion-size.svg)](https://pypi.org/project/fashion-size/)
[![License: BSD-3-Clause](https://img.shields.io/pypi/l/fashion-size.svg)](https://github.com/ababic/fashion-size/blob/main/LICENSE)
[![Tests](https://github.com/ababic/fashion-size/actions/workflows/test.yml/badge.svg)](https://github.com/ababic/fashion-size/actions/workflows/test.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Typed](https://img.shields.io/badge/typed-py.typed-ff69b4)](https://github.com/ababic/fashion-size/tree/main/src/fashion_size/py.typed)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-2ea44f)](https://pypi.org/project/fashion-size/)

Size types (UK dress size, EU adult shoe size, chest in centimetres) and the charts that convert them. Clothing and footwear share this library.

```bash
pip install fashion-size
```

Requires Python 3.12 or newer. There are no runtime dependencies.

Default UK / EU / US / AU charts are in Python. Brand charts that differ from those defaults ship as JSON: the rows, the source page, and notes live with the chart, and the date it was last checked lives in the brand catalog.

This package does not depend on Django. Django model fields are in [`django-fashion-size`](https://github.com/ababic/django-fashion-size).

The source repository is [github.com/ababic/fashion-size](https://github.com/ababic/fashion-size).

## Size types and conversion behavior

`fashion-size` supports three conversion models:

- **Brand-variable chart lookup**: the size type can use default scales or brand overrides.
- **Fixed default chart lookup**: the size type always uses shipped default scales.
- **Fixed formula conversion**: conversion is direct (`in` <-> `cm`), not chart-based.

| Size type | Common size units | Conversion model | How units vary |
| --- | --- | --- | --- |
| Dress (`dress`) | `uk-dress-size`, `eu-dress-size`, `us-dress-size`, `au-dress-size` (`fr-dress-size` resolves to EU) | Brand-variable chart lookup | Regional numeric labels. French dress labels are the EU value. |
| Adult shoe (`adult-shoe`) | `uk-adult-shoe-size`, `eu-adult-shoe-size`, `us-adult-shoe-size`, `au-adult-shoe-size` (`fr-adult-shoe-size` resolves to EU) | Brand-variable chart lookup | Numeric rows vary by locale; alpha shoe labels (`XXS` ... `XXL`) are accepted and convert identically across UK/EU/US/AU. |
| Kids shoe (`kids-shoe`) | `uk-kids-shoe-size`, `eu-kids-shoe-size`, `us-kids-shoe-size`, `au-kids-shoe-size` (`fr-kids-shoe-size` resolves to EU) | Brand-variable chart lookup | Same unit behavior as adult shoes, but with the kids shoe chart lineage. The default chart covers children and babies (one chart for every gender). Baby shoe sizes (UK 0–5.5) stay on the baby shoe chart. |
| Baby shoe (`baby-shoe`) | `uk-baby-shoe-size`, `eu-baby-shoe-size`, `us-baby-shoe-size`, `au-baby-shoe-size` (`fr-baby-shoe-size` resolves to EU) | Brand-variable chart lookup | Same unit behavior as other shoes, but with the baby shoe chart lineage. |
| Cup (`cup-size`) | `uk-cup-size`, `eu-cup-size`, `us-cup-size`, `au-cup-size` (`fr-cup-size` resolves to EU) | Brand-variable chart lookup | Letter mappings differ across locales (`DD`/`E`/`DDD` etc). Alpha cup labels (`XXS`, `XS`, `S`, `MD`, `LG`, `XL`, `XXL`) are locale-identity values. |
| Band (`band-size`) | `uk-band-size`, `eu-band-size`, `us-band-size`, `au-band-size`, `fr-band-size` | Fixed default chart lookup | UK/US are inch labels, EU is centimetre label, AU is dress-style number, and FR is EU + 15. Brand overrides are intentionally disabled for this type. |
| Waist label (`waist-size`) | `uk-waist-size`, `eu-waist-size`, `us-waist-size`, `au-waist-size` | Brand-variable chart lookup | UK/US/AU waist labels are inch-based. EU waist is a shared regional unit: adult rows use continental labels, while child rows use centimetres. |
| Chest label (`chest-size`) | `uk-chest-size`, `eu-chest-size`, `us-chest-size`, `au-chest-size` (`fr-chest-size` resolves to EU) | Brand-variable chart lookup | UK/US/AU chest labels are inch-based. EU chest is a shared regional unit: adult rows use continental labels, while child rows use centimetres. French chest labels match EU. |
| Body measurements (`chest`, `waist`, `collar`, `sleeve`) | `cm-chest-size`, `in-waist-size`, `in-collar-size`, `in-sleeve-length`, etc. | Fixed formula conversion | Tape-measure style values in `in`/`cm`. Bounds: chest 18–88, waist 16–85, collar 11–28, sleeve 28–40. A dress shirt `15.5/34` is collar and sleeve, both inches. Each exposes `length_range` on the size type. |
| Leg length / inseam (`inside-leg`, `shorts-inseam`, `trousers-inseam`) | `in-inside-leg`, `in-shorts-inseam`, `in-trousers-inseam`, and `cm-*` pairs | Fixed formula conversion | Garment inside-leg / inseam in `in`/`cm`. Prefer `shorts-inseam` (2–22 in) or `trousers-inseam` (24–42 in) on product data so values cannot sit on the wrong attribute. Generic `inside-leg` / `leg-length` accepts 2–42 in when the catalog has not split shorts vs trousers. |
| Label sizes (`trouser-length`, `top-length`, `shoe-width`, `proportion`, `age-months`, `age-years`, `letter`) | one universal unit per type (`trouser-length`, `letter`, …) | None | Sold-as words, age bands, and generic letter sizes (`XXS` through `6XL`, plus `ONE` for one size). `raw` is a canonical token (`regular`, `extra-wide`, `5-6`, `2XL`). Month units include `months`, `month`, `mths`, `mth`, and `m`. Synonyms fold in (`R`, `std`, `XXL`, `small`). They are not on locale charts. |

Today, shipped brand overrides are concentrated in selected dress and shoe charts. Types still marked as brand-variable above continue to fall back to default scales when no matching brand chart exists for the brand, demographic, product type, and `as_of` capture instant.

## Size description strings

`fashion_size.descriptions` is imported only when you call it. It recognises common feed strings and joins size values back into one string. The product type's family chooses how an unlabelled number is read. Chart sizes stay in the region they were written in. Length values can move between inches and centimetres. Label wording follows `preferred_regions`, from the vocabulary on the label size type.

```python
from fashion_size.descriptions import decode_size_description, encode_size_description
from fashion_size.product_types import ProductType
from fashion_size.types import Locale

decoded = decode_size_description("30/32", Locale.UK, product_type=ProductType.JEANS)
decoded.format_id  # "waist-leg"
decoded.confidence
decoded.sizes

encode_size_description(
    decoded.sizes, Locale.UK, preferred_regions=(Locale.UK, Locale.EU)
).text
```

`confidence` drops when another format was also plausible. `discarded` lists tokens that were duplicates, ranges, out of the target length range, or not recognised. A range such as `UK 8-10` is not a size. A cell with several regions, such as `EU 38 / UK 10` or `41 (UK 7.5)`, returns each region. `preferred_regions` then keeps the first of those that is present. Omit it and `source_region` is used. Chart sizes are not converted onto a chart. A length that cannot be converted into the preferred unit is discarded with reason `out-of-range`.

A bra string such as `32DD` is a UK inch band from 28 to 56 plus a cup letter, in whichever region the cell was written. On a dress, skirt, nightwear, or swimwear product the cup letter is ignored. A French prefix is folded onto EU before an unlabelled number in the adult shoe span (35–50) is read as a shoe size, so a lone `EU 40` or `FR 40` with no product type is an EU adult shoe size. A French band outside that span, such as `FR 90`, stays a band size.

## Brand charts

```python
from fashion_size import SUPPORTED_BRANDS, ProductType
from fashion_size.charts import chart_for, load_brand_charts

"Dune London" in SUPPORTED_BRANDS
chart = chart_for("Dune London", "adult-shoe", "adult", "female", product_type=ProductType.SHOES)
chart.updated_at
chart.effective_from
chart.effective_until
chart.source_url
chart.source_notes
chart.rows
```

`ProductType` is the list of ranges a brand chart can cover on its own (jeans, trousers, shorts, skirts, bras, swimwear, nightwear, hosiery, outerwear, shoes, boots, and so on). A chart names the product types it replaces. Each product type belongs to a `ProductTypeFamily` (`bottoms`, `tops`, `footwear`, `dresses`, `bras`, `other`). A family is the shared way of reading an unlabelled size: jeans and trousers are both bottoms, dresses and skirts are both dresses. A product type's profile adds the cases that are not shared, such as a suit chest size or a dress-shirt collar and sleeve.

Each override chart is a JSON file named by id under `src/fashion_size/fixtures/charts`. The file holds the rows, the source page, and any notes about that table. Which brand it belongs to, the size type and demographic, when it was last checked, and when its rows take effect live in `fashion_size.brands`. A later chart for the same size type, demographic, and product types replaces the earlier one: `effective_until` is that next start, or none while the chart is current. A brand with no charts there matches the default charts. Superseded charts stay in the catalog.

`chart_for` takes an optional `as_of` timestamp, the instant the raw size was captured. Omit it to use the latest matching chart generation. A capture time before the first chart in a series returns none.

## Conversion

```python
from fashion_size import Demographic, ProductType
from fashion_size.types import UK_ADULT_SHOE_SIZE, UK_DRESS_SIZE, Size

women = Demographic("adult", "female")
value = Size.from_raw("10", UK_DRESS_SIZE)
value.convert_to_locale("eu", demographic=women)

shoe = Size.from_raw("7", UK_ADULT_SHOE_SIZE)
shoe.convert_to_locale(
    "eu",
    demographic=women,
    brand_name="Dune London",
    product_type=ProductType.SHOES,
)
```

`convert` takes a `SizeUnit` on the same size type, or `"cm"` / `"in"` for a length. `convert_to_locale` resolves a locale such as `"eu"` to that size type's `SizeUnit` and calls `convert`. Both require a `Demographic` (age group and gender). Optional `brand_name` and `product_type` select a brand chart. Optional `as_of` is when the raw size was captured; omit it to use the latest matching brand chart generation and the current default chart. Set `strict_brand_name=True` to reject a brand name that is not in `SUPPORTED_BRANDS`.

Both return a `ConvertedSize` with the resulting size and a `ConversionSource` (`identity`, `default`, `brand`, or `length_formula`). When the default chart is used, `source.default_reason` says why: no brand was passed (`no_brand`), the name is not in the catalog (`unknown_brand`), the catalog brand has no override charts (`brand_uses_default`), or the brand has no chart for this size type, product type, and capture time (`no_matching_chart`). Band size with a brand name records `size_type_uses_default`. `ConvertedSize` has no conversion method, so a converted value is not converted again.

Default charts use the same windows. The charts shipped in this package apply from the first representable instant until a later default for that size type and demographic replaces them. A capture time before a brand's first override uses the default chart that was in force then.

### Chart age coverage

A **size type** defines the numeric scale on the attribute (`kids-shoe`, `baby-shoe`, …). A **catalogue age group** (`child`, `baby`, `adult`) is how the product is filed. `fashion_size.chart_coverage.CHART_AGE_COVERAGE` lists, per size type, every catalogue age that may use that type's conversion charts.

| Size type | Catalogue ages covered | Notes |
| --- | --- | --- |
| `baby-shoe` | `baby` | UK 0–5.5 scale |
| `kids-shoe` | `child`, `baby` | UK 6+ youth scale; same rows whether the item is filed as child or baby |
| `adult-shoe` | `adult` | |
| `dress` | `adult`, `child` | Separate default row sets per age |
| `waist-size`, `chest-size` | `adult`, `child` | Kids rows are child-only; no baby waist/chest charts |
| `cup-size`, `band-size` | `adult` | |

Lookup tries charts stored under the product's age first. For `kids-shoe` on a **baby** label, a brand override filed under **`child`** is used when there is no baby chart — the same rule as the default kids shoe chart. Other size types do not fall back across catalogue ages.

`brand_name` may be any string. A `BrandName` selects that brand's chart. Any other name uses the default chart unless `strict_brand_name` is set. An unknown `product_type` is an error.

French dress, shoe, cup, and chest labels are the EU size (`"fr"` converts to that EU value). French band size is the EU centimetre label plus 15. French waist size is not on the chart. Length size types convert between centimetres and inches (`1 in = 2.54 cm`) only inside each type's inch bounds (see the conversion table). Display rounding (nearest centimetre, nearest half inch) does not change the stored value.

Each length size type exposes inclusive bounds on the type itself: `SHORTS_INSEAM.length_range_start` / `length_range_stop`, or `SHORTS_INSEAM.length_range` (`start_inches`, `stop_inches`, and centimetre properties). These are fixed per size type, not read from locale charts. The same range is available on `SizeUnit.length_range` (for example `INCH_SHORTS_INSEAM.length_range`). `length_entry_bounds(size_type)` returns the same limits as min/max fields for form widgets. Use `length_value_in_range(raw, size_unit)` to validate an entry against the attribute's size unit. When a number could belong to more than one leg-length attribute, `length_size_types_for_inches` and `length_size_types_for_measurement` list matching types with the narrowest span first (garment inseams before generic inside leg). By default they consider `shorts-inseam`, `trousers-inseam`, and `inside-leg` only; pass `candidates=` to widen (for example `LENGTH_SIZE_TYPES`) or narrow to garment inseams. `size_from_attribute_option` returns `None` for length values outside the attribute's bounds.

UK, US, and AU waist and chest labels are the inch measurement, so they display like a length (`30"`, `30 in`). A UK or US band is the underbust in inches; an EU band is centimetres (`75cm`, `75 cm`). An EU waist or chest label stays regional (`EU 46`): adult charts use a different number, and children's charts store centimetres, on one shared size unit. An AU band is a dress-style number (`AU 12`). A French band keeps its own number (`FR 90`).

Sports bras and bralettes can use alpha cup labels on the same size type. Stored values are `XXS`, `XS`, `S`, `MD`, `LG`, `XL`, and `XXL` (`CUP_ALPHA_ORDER`). Common aliases (`small`, `med`, `medium`, `lg`, `large`, `x-large`, `2xl`) normalise to those. They convert identically across UK / EU / US / AU. `Size.display` shows `MD` / `LG` as `M` / `L`; `raw` stays `MD` / `LG`. Single-letter `m` and `l` are bra cup letters, so a feed that means alpha must send `MD` / `LG` (or `medium` / `large`) — do not persist the short display and parse it again. These labels are not rows on the letter chart. `cup_attribute_values` appends them after the chart letters for a locale, and `cup_sort_key` orders letters by chart row, then alpha from `XXS` to `XXL`.

Shoe sizes can also use alpha labels (`XXS`, `XS`, `S`, `M`, `L`, `XL`, `XXL`) on the existing shoe size types (`adult-shoe`, `kids-shoe`, `baby-shoe`). Common aliases (`small`, `medium`, `large`, `x-large`, `2xl`) normalise to canonical tokens. These alpha labels convert identically across UK / EU / US / AU and are not rows on numeric charts. `shoe_attribute_values(size_unit, age_group=..., gender=...)` appends them after the chart values for that demographic.

Display language defaults to `en-gb`. A host application can register its own getter (Django's `get_language`, for example) with `fashion_size.register_display_language`.

## Development

```bash
pip install -e ".[testing,development]"
pytest
ruff check src tests
```

## Releasing

Publishing uses [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/). On PyPI, add a pending publisher for the `fashion-size` project:

- Owner: `ababic`
- Repository: `fashion-size`
- Workflow: `release.yml`
- Environment: `pypi`

Create a GitHub environment named `pypi` (no secrets).

### Version numbers (CalVer)

Releases use [calendar versioning](https://calver.org/): `YYYY.M.D` (UTC date when the release is tagged), for example `2026.10.5`. Git tags are `v` plus that string (`v2026.10.5`). The tag without the `v` must match `fashion_size.__version__`.

For a second release on the same UTC day, bump the micro segment: `2026.10.5.1` and tag `v2026.10.5.1` (or use `.post1` if you prefer PEP 440 post-releases).

Before tagging, bump `src/fashion_size/__version__.py`, update `CHANGELOG.md`, commit, then push the tag. The tagged commit must be on `main` or a branch named `release-*`. The workflow runs tests, checks that the tag matches the package version, builds wheels, creates a GitHub release, and publishes to PyPI. A tag whose commit is not on one of those branches fails before anything is published.

## License

BSD 3-Clause. See [LICENSE](https://github.com/ababic/fashion-size/blob/main/LICENSE).
