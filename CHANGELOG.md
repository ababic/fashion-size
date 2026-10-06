# Changelog

## Unreleased

- `ProductType.SWIMWEAR`, `OUTERWEAR`, `CASUAL_BOTTOMS`, `NIGHTWEAR`, `BRAS`, `SKIRTS`, and `SHORTS` for brand charts that cover those ranges on their own.

## 2026.10.5

- Release numbering follows CalVer (`YYYY.M.D`, UTC); see README.

## 1.0.0

- Standalone conversion API: `Size.convert` and `Size.convert_to_locale` with required `Demographic`, optional `brand_name`, `product_type`, and `strict_brand_name`.
- `ConvertedSize` exposes `ConversionSource` provenance (`identity`, `default`, `brand`, `length_formula`) and `DefaultChartReason` when the default chart is used.
- Built-in brand chart resolution; removed host `register_brand_converter`.
- `BrandName` and `ProductType` enums for catalog spellings.

## 0.1.0

- Initial release: size types and size units, UK / EU / US / AU / FR conversion, and brand size charts.
- Each override chart is a JSON file named by id, holding the rows, source page, and notes. Brand, review date, and whether the guide differs from the default live in Python.
