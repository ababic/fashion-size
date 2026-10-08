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

## Brand charts

```python
from fashion_size import SUPPORTED_BRANDS, ProductType
from fashion_size.charts import chart_for, load_brand_charts

"Dune London" in SUPPORTED_BRANDS
chart = chart_for("Dune London", "adult-shoe", "adult", "female", product_type=ProductType.SHOES)
chart.updated_at
chart.source_url
chart.source_notes
chart.rows
```

`ProductType` is the list of ranges a brand chart can cover on its own (jeans, trousers, shorts, skirts, bras, swimwear, nightwear, hosiery, outerwear, shoes, boots, and so on). A chart names the product types it replaces.

Each override chart is a JSON file named by id under `src/fashion_size/fixtures/charts`. The file holds the rows, the source page, and any notes about that table. Which brand it belongs to, the size type and demographic, and when it was last checked live in `fashion_size.brands`. A brand with no charts there matches the default charts.

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

`convert` takes a `SizeUnit` on the same size type, or `"cm"` / `"in"` for a length. `convert_to_locale` resolves a locale such as `"eu"` to that size type's `SizeUnit` and calls `convert`. Both require a `Demographic` (age group and gender). Optional `brand_name` and `product_type` select a brand chart. Set `strict_brand_name=True` to reject a brand name that is not in `SUPPORTED_BRANDS`.

Both return a `ConvertedSize` with the resulting size and a `ConversionSource` (`identity`, `default`, `brand`, or `length_formula`). When the default chart is used, `source.default_reason` says why: no brand was passed (`no_brand`), the name is not in the catalog (`unknown_brand`), the catalog brand has no override charts (`brand_uses_default`), or the brand has no chart for this size type and product type (`no_matching_chart`). Band size with a brand name records `size_type_uses_default`. `ConvertedSize` has no conversion method, so a converted value is not converted again.

`brand_name` may be any string. A `BrandName` selects that brand's chart. Any other name uses the default chart unless `strict_brand_name` is set. An unknown `product_type` is an error.

French dress, shoe, cup, and chest labels are the EU size (`"fr"` converts to that EU value). French band size is the EU centimetre label plus 15. French waist size is not on the chart. Lengths convert between centimetres and inches (`1 in = 2.54 cm`) for values from 5 to 150 inches. Display rounding (nearest centimetre, nearest half inch) does not change the stored value.

Sports bras and bralettes can use alpha cup labels on the same size type. Stored values are `XXS`, `XS`, `Small`, `Medium`, `Large`, `XL`, and `XXL` (`CUP_ALPHA_ORDER`). Common aliases (`s`, `med`, `lg`, `x-large`, `2xl`) normalise to those. They convert identically across UK / EU / US / AU. `Size.display` shortens `Small` / `Medium` / `Large` to `S` / `M` / `L`; `raw` stays the stored word. Single-letter `m` and `l` are bra cup letters, so a feed that means alpha must send `Medium` / `Large` (or `med` / `lg`) — do not persist the short display and parse it again. These labels are not rows on the letter chart. `cup_attribute_values` appends them after the chart letters for a locale, and `cup_sort_key` orders letters by chart row, then alpha from `XXS` to `XXL`.

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

Before tagging, bump `src/fashion_size/__version__.py`, update `CHANGELOG.md`, commit, then push the tag. The workflow runs tests, checks that the tag matches the package version, builds wheels, creates a GitHub release, and publishes to PyPI.

## License

BSD 3-Clause. See [LICENSE](https://github.com/ababic/fashion-size/blob/main/LICENSE).
