# Changelog

## 2026.10.8

- Cup size accepts sports-bra alpha labels (`XXS`, `XS`, `Small`, `Medium`, `Large`, `XL`, `XXL`) with common aliases. They convert identically across UK / EU / US / AU. Single-letter `l` and `m` remain bra cup letters.

## 2026.10.6

- `ProductType.SWIMWEAR`, `OUTERWEAR`, `CASUAL_BOTTOMS`, `NIGHTWEAR`, `BRAS`, `SKIRTS`, `SHORTS`, and `HOSIERY` (tights, stockings, and socks) for brand charts that cover those ranges on their own.
- `ProductType.SUITS` is labelled `"Suits & Tailoring"`. `suit-jackets` is removed; the slug `"suit-jackets"` still resolves to `suits`.

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
