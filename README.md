# fashion-size

Kind-specific fashion measurements (UK dress size, EU adult shoe size, chest in centimetres) and the charts that convert them. Clothing and footwear share this library.

Default UK / EU / US / AU charts are in Python. Brand charts that differ from those defaults ship as JSON, with the date they were last checked, the source page, and notes.

This package does not depend on Django. Django model fields are in [`django-fashion-size`](https://github.com/ababic/django-fashion-size).

The source repository is [github.com/ababic/fashion-size](https://github.com/ababic/fashion-size). PyPI packaging comes later.

## Brand charts

```python
from fashion_size import SUPPORTED_BRANDS, OverrideGuide
from fashion_size.charts import chart_for, load_brand_charts

"Dune London" in SUPPORTED_BRANDS
chart = chart_for("Dune London", "adult-shoe", "adult", "female", guide=OverrideGuide.SHOES)
chart.updated_at
chart.source_url
chart.source_notes
chart.rows
```

`OverrideGuide` is the list of families a brand chart can cover on its own (jeans, trousers, shoes, boots, and so on). A chart names the families it replaces.

## Conversion

```python
from fashion_size.types import UK_DRESS_SIZE, MeasurementValue

value = MeasurementValue.from_raw("10", UK_DRESS_SIZE)
value.convert("eu", age_group="adult", gender="female")
```

Display language defaults to `en-gb`. A host application can register its own getter (Django's `get_language`, for example) with `fashion_size.register_display_language`. Brand-specific conversion is supplied the same way, via `fashion_size.register_brand_converter`.
