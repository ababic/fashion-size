# AGENTS.md

Guidance for agents working in this repository (`fashion-size`).

## 1) Project overview

- This repo is a pure-Python library for clothing/footwear size conversion.
- Runtime dependencies are intentionally empty.
- Python support is `>=3.12`.
- Main public API is exposed from `fashion_size` and `fashion_size.types`.
- Conversion behavior is chart-driven:
  - Default charts are defined in Python (`scales.py`).
  - Brand overrides are defined by metadata in `brands.py` plus row files in `fixtures/charts/*.json`.

## 2) Repository map (where to change what)

- `src/fashion_size/types.py`
  - Core domain objects (`Size`, `SizeUnit`, conversion source metadata, parsing/display helpers).
- `src/fashion_size/conversion.py`
  - Conversion execution logic (`convert`, `convert_to_locale`, chart/default resolution flow).
- `src/fashion_size/charts.py`
  - Brand chart loading, validation, and chart selection (`chart_for`).
- `src/fashion_size/scales.py`
  - Built-in default conversion scales and effective-window lookup.
- `src/fashion_size/brands.py`
  - Brand catalog and override chart metadata (`OverrideChart`).
- `src/fashion_size/product_types.py`, `size_types.py`, `demographics.py`
  - Canonical enums/labels/resolvers used by lookup logic.
- `tests/test_fashion_size.py`
  - Primary behavior regression suite (single comprehensive test module).
- `README.md`, `CHANGELOG.md`
  - User-facing behavior and release notes; keep in sync with behavior changes.
- `src/fashion_size/__version__.py`
  - Source of package version truth.

## 3) Non-negotiable behavior invariants

- `as_of` handling:
  - `as_of` is optional in conversion/chart lookup APIs.
  - Omitted `as_of` must use:
    - latest matching brand chart generation (for brand lookups), and
    - current default scale.
  - Provided `as_of` must be timezone-aware; naive datetimes are invalid.
- Effective windows:
  - Chart generation windows are `[effective_from, effective_until)`.
  - In a lineage, duplicate `effective_from` instants are invalid.
- Brand chart fixtures:
  - JSON file schema/version and row format are strict.
  - Every chart ID in metadata must map to exactly one fixture file, and vice versa.
- Conversion source metadata (`ConversionSourceKind`, `DefaultChartReason`) is part of behavior; avoid silent changes.

## 4) Coding conventions for this codebase

- Prefer fewer, larger cohesive functions over over-fragmented helper chains.
- Keep imports at module top by default.
  - Only inline imports when needed to break a verified circular import problem.
- Preserve strong typing and existing style (`dataclass(frozen=True, slots=True)`, enums, explicit return types).
- Keep logic explicit and deterministic; avoid assumptions when behavior can be proven by tests.
- If you change behavior, update docs (`README.md`) and release notes (`CHANGELOG.md`) in the same PR unless explicitly told otherwise.

## 5) Development and validation commands

Install dev deps:

```bash
pip install -e ".[testing,development]"
```

Fast validation loop:

```bash
pytest tests/test_fashion_size.py -k "<targeted-expression>"
```

Full local gate (matches CI intent):

```bash
pytest tests/test_fashion_size.py
ruff check src tests
```

CI runs:

- Tests on Python `3.12`, `3.13`, `3.14`.
- Ruff lint on Python `3.12`.
- Wheel build/install smoke check.

## 6) Playbook: changing conversion logic

When editing `conversion.py`, `charts.py`, or `scales.py`:

1. Add/adjust targeted regression tests in `tests/test_fashion_size.py`.
2. Validate both:
   - happy path conversion values, and
   - provenance (`source.kind`, `default_reason`, selected chart identity where relevant).
3. Run targeted tests first, then full test module + Ruff.
4. Update README/CHANGELOG if observable behavior changed.

## 7) Playbook: changing brand chart data

When adding/updating brand overrides:

1. Update metadata in `brands.py` (`OverrideChart` entry).
2. Add/update corresponding JSON file under `src/fashion_size/fixtures/charts/`.
3. Keep chart IDs lowercase UUIDs.
4. Ensure timezone-aware `updated_at` and `effective_from`.
5. Run tests covering chart catalog/fixture integrity and conversion behavior.

## 8) Release/versioning checklist

This repo uses CalVer (`YYYY.M.D`, optional micro like `YYYY.M.D.1`).

For release-ready changes:

1. Bump `src/fashion_size/__version__.py`.
2. Update the version assertion in `tests/test_fashion_size.py`.
3. Update `CHANGELOG.md`.
4. Run full tests and lint.

Tagging/publish notes:

- Release workflow expects tag format `v<version>`.
- Tagged commit must be on `main` or `release-*`.
- Workflow checks tag/version match before publishing.

## 9) PR quality checklist

Before opening/updating a PR, verify:

- [ ] Behavior changes are covered by tests.
- [ ] `pytest tests/test_fashion_size.py` passes.
- [ ] `ruff check src tests` passes.
- [ ] Docs/changelog updates are included when behavior changed.
- [ ] Version bump is included when explicitly requested for immediate release.
