# Changelog

## Unreleased

## 2026.10.20

- Label size types, their units, and label sizes can be hashed. A vocabulary stores its token pairs as tuples.
- With no product type, a lone `EU` or `FR` number in the adult shoe span (35–50) is an EU adult shoe size. `FR 90` stays a French band. A cup letter on a dress, skirt, nightwear, or swimwear product is not read as a cup size.
- Encoding a length that falls outside the target unit's range discards it with reason `out-of-range`. Feed bra strings such as `32DD` stay UK inch bands (28–56).
- A numbered fit such as `16L` on a dress or top is a dress size plus proportion `long`. That code used to raise.
- Each `ProductType` belongs to a `ProductTypeFamily` (`bottoms`, `tops`, `footwear`, `dresses`, `bras`, `other`) and carries a `ProductTypeProfile` for the readings that are not shared: a suit or outerwear number in the jacket range is a chest size, and a shirt can pair a collar with a sleeve. Feed decoding asks the family and the profile. Each size type names the product types it belongs with. Label size types own their tokens, synonyms, and regional wording.
- `sleeve` length size type (28–40 in). A dress shirt `15.5/34` is collar and sleeve, both inches.
- Description decoding skips exception phrases that look like sizes: pack counts, years, `Petite Edit`, and `long sleeve`.
- Label size types `trouser-length`, `top-length`, `shoe-width`, `proportion`, `age-months`, `age-years`, and `letter`. Tokens are canonical (`regular`, `extra-wide`, `5-6`, `2XL`, `ONE`). Month bands accept `months`, `month`, `mths`, `mth`, and `m`. Letter sizes accept `S`/`small`, `XXL`/`2XL`, and `one size`. They do not use conversion charts.
- `fashion_size.descriptions.decode_size_description` and `encode_size_description` recognise feed size strings and join size values back into one string. The module is not imported with the package. `source_region`, `preferred_regions`, and `product_type` take `Locale` and `ProductType` values. Chart sizes stay in the region they were found in. Length values can move between inches and centimetres for a preferred region. Results include a confidence score and discarded tokens.

## 2026.10.17

- `shorts-inseam` and `trousers-inseam` length size types with non-overlapping inch bounds 2–22 and 24–42 (retail-aligned, with headroom for long shorts and big-and-tall trousers). Formula conversion rejects values outside each type's range. Generic `inside-leg` keeps the 5–150 inch clothing range.
- `LengthRange` on each length `SizeType` via `length_range`, plus `length_range_start` and `length_range_stop` (and the same on `SizeUnit`), so hosts can read inclusive bounds without locale charts.
- `length_entry_bounds`, `length_value_in_range`, and `length_size_types_for_inches` / `length_size_types_for_measurement` for form min/max and inferring which length attribute a raw value might represent. `size_from_attribute_option` rejects out-of-range length values.
- Realistic inch bounds on formula length types: chest 18–88, waist 16–85, collar 11–28; generic `inside-leg` 2–42 in (inseam span when shorts/trousers are not split).
- Brand and default conversion charts keep earlier generations. `effective_from` is when a chart's rows start to apply. `effective_until` is the next chart's start for the same size type, demographic, and product types. `chart_for`, `Size.convert`, and `Size.convert_to_locale` take optional `as_of`, the instant the raw size was captured. Omit it to use the latest matching brand chart generation and the current default chart. A capture time before a brand's first override uses the default chart. Loaded brand charts include their catalog `id`.
- The release workflow publishes a `v*` tag only when that commit is on `main` or a `release-*` branch.

## 2026.10.10

- Shoe sizes accept alpha labels (`XXS`, `XS`, `S`, `M`, `L`, `XL`, `XXL`) with common aliases on adult, kids, and baby shoe size types. They convert identically across UK / EU / US / AU. Alpha labels are not rows on numeric charts. `shoe_attribute_values` appends them after chart values for a demographic.

## 2026.10.8.1

- UK, US, and AU waist and chest sizes, and UK, US, and EU band sizes, display as inches or centimetres with the same language rules as length. EU waist and chest labels, AU bands, and French bands keep a region prefix.

## 2026.10.8

- Cup size accepts sports-bra alpha labels (`XXS`, `XS`, `S`, `MD`, `LG`, `XL`, `XXL`) with common aliases. They convert identically across UK / EU / US / AU. Single-letter `l` and `m` remain bra cup letters. Display shows `MD` / `LG` as `M` / `L`; `raw` stays canonical. `cup_attribute_values` and `cup_sort_key` cover option lists, because alpha labels are not rows on the letter chart.

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
