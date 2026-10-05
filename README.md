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

`ProductType` is the list of ranges a brand chart can cover on its own (jeans, trousers, shoes, boots, and so on). A chart names the product types it replaces.

Each override chart is a JSON file named by id under `src/fashion_size/fixtures/charts`. The file holds the rows, the source page, and any notes about that table. Which brand it belongs to, the size type and demographic, and when it was last checked live in `fashion_size.brands`. A brand with no charts there matches the default charts.

## Conversion

```python
from fashion_size.types import UK_DRESS_SIZE, Size

value = Size.from_raw("10", UK_DRESS_SIZE)
value.convert("eu", age_group="adult", gender="female")
```

French dress, shoe, cup, and chest labels are the EU size (`"fr"` converts to that EU value). French band size is the EU centimetre label plus 15. French waist size is not on the chart. Lengths convert between centimetres and inches (`1 in = 2.54 cm`) for values from 5 to 150 inches. Display rounding (nearest centimetre, nearest half inch) does not change the stored value.

Display language defaults to `en-gb`. A host application can register its own getter (Django's `get_language`, for example) with `fashion_size.register_display_language`. Brand-specific conversion is supplied the same way, via `fashion_size.register_brand_converter`.

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

Create a GitHub environment named `pypi` (no secrets). Tag `v0.1.0` — the tag must match `fashion_size.__version__` — to test, build the distributions, attach them to a GitHub release, and publish to PyPI.

## License

BSD 3-Clause. See [LICENSE](https://github.com/ababic/fashion-size/blob/main/LICENSE).
