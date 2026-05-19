# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install dependencies
uv run ruff check .            # lint
uv run ruff format .           # format
pre-commit run --all-files     # run all pre-commit hooks (ruff lint + format + yaml check)
```

There is no test suite. Exploratory analysis lives in `notebooks/`.

## Architecture

The project scrapes EU ETS (Emissions Trading System) data from the EUTL (EU Transaction Log) and publishes it as a [Frictionless Data Package](https://specs.frictionlessdata.io/).

### Central config: `Settings`

[`eutl_scraper/settings.py`](../eutl_scraper/settings.py) — `Settings(dir_data=...)` is passed to every pipeline function. It resolves all file paths via `settings.fp(key, directory)` where `key` is a name from `Settings.FILENAMES` and `directory` is either `settings.dir_source` (raw downloads) or `settings.dir_extracted` (cleaned CSVs). Never construct file paths manually; always use `settings.fp()`.

The same file contains `DownloadClient`, an `httpx`-based HTTP client with automatic byte-range resume on dropped connections.

### Data flow

```
[remote sources] → dir_source/ (raw CSVs) → dir_extracted/ (normalized CSVs) → data package ZIP
```

### Pipelines

The top-level entry point is `get_all_data()` in [`eutl_scraper/pipelines.py`](../eutl_scraper/pipelines.py). It dispatches to four pipelines registered in `PIPELINE_REGISTRY`:

| Pipeline enum | Module | What it does |
|---|---|---|
| `EUTL` | `eutl_scraper/eutl/` | Main pipeline: download + extract + augment |
| `EEX_AUCTIONS` | `eutl_scraper/other/eex_auctions/` | EUA primary auction prices from EEX |
| `NACE_FROM_LEAKAGE_LISTS` | `eutl_scraper/other/nace_codes/` | NACE codes from bundled leakage list Excel files |
| `INSTALLATION_COORDINATES` | `eutl_scraper/other/locations/` | Geocode installations via Geoapify API |

`eutl_scraper/pipeline/__init__.py` defines a `BasePipeline` ABC (fetch / extract / augment) that is the intended future interface — existing pipelines are plain functions, not yet migrated.

### EUTL pipeline (`eutl_scraper/eutl/`)

Three steps controlled by `EUTLPipelineSteps`:

1. **DOWNLOAD** (`download.py`): fetches accounts, installations, compliance as gzipped CSVs from Azure Blob Storage, and transactions as a ZIP from EC. Saves raw files to `dir_source/`.

2. **EXTRACT** (`extract/`): one module per entity — `accounts.py`, `installations.py`, `compliance.py`, `transactions.py`, `account_holders.py`. Each follows: read raw CSV → clean/rename → validate → save to `dir_extracted/`. Account holders require a **manually downloaded Excel file** (from the EUTL PowerBI portal, not available via automated download).

3. **AUGMENT** (`augment/`):
   - `installations.py`: detects installations in compliance but missing from the installations table and creates stub rows tagged `ets_id="ETS2"` (expected ≤30; aborts if more).
   - `accounts.py`: scans transaction parties for `account_id`s absent from the accounts table and appends them with limited metadata.

### Key identifiers

- `account_id` = `"{registry_code}_{account_identifier}"` (e.g. `"DE_12345"`)
- `installation_id` = `"{registry_code}_{installation_identifier}"` (e.g. `"DE_98765"`)
- `registry_id` = two-letter country code; mapping in `eutl_scraper/eutl/mappings.py`

### Publication layer (`eutl_scraper/publish/`)

`TABLE_REGISTRY` maps table names to `BaseConfig` subclasses. Each config holds:
- `column_mapping`: raw → published column name renaming
- `type_convertors`: per-column callables applied before renaming
- `transformers`: additional DataFrame transforms
- `schema_path`: YAML schema file under `publish/schemas/` (Frictionless field descriptors)

`publish_data_package()` reads each extracted CSV, runs it through `prepare_table()` and `create_resource()` (which validates against the YAML schema), then writes a ZIP bundle with all CSVs and `datapackage.yaml`/`.json`.

To add a new output table: create a `BaseConfig` subclass, add a YAML schema, register it in `TABLE_REGISTRY`, and add the path to `data_paths` in `publish_data_package()`.

### NACE codes pipeline

Uses two static Excel leakage lists (`leakage_2015.xlsx`, `leakage_2020.xlsx`) and an HTML NACE scheme file, all bundled in `eutl_scraper/other/nace_codes/`. No downloads required.

### Geocoding pipeline

Calls the Geoapify REST API. Requires `api_keys={"geoapify": "<key>"}` passed to `get_all_data()`. Skips activity types 10 (aircraft) and 50 (shipping). Caches addresses within a single run to avoid duplicate API calls. The `max_installations` parameter is available for local testing.
