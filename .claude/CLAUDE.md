# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install dependencies
uv run ruff check .            # lint
uv run ruff format .           # format
pre-commit run --all-files     # run all pre-commit hooks (ruff lint + format + yaml check)
```

There is no test suite. Exploratory analysis lives in `notebooks/`. Architecture decisions are
recorded under [`.ai-context/`](../.ai-context/) (`CONTEXT.md` + numbered ADRs) — read those before
making structural changes.

## Architecture

The project scrapes EU ETS (Emissions Trading System) data from the EUTL (EU Transaction Log) plus a
few related sources, normalises it, and publishes it as a
[Frictionless Data Package](https://specs.frictionlessdata.io/).

### Two entry points

1. **Acquire + clean** — `AllDataBundle(settings, api_keys, max_installations).run()`
   ([`eutl_scraper/bundles.py`](../eutl_scraper/bundles.py)). Runs every fetch/extract/augment
   pipeline; writes raw files to `dir_source/` and cleaned parquet to `dir_extracted/`. See
   [`main.py`](../main.py).
2. **Publish** — `publish_data_package(settings, fn_out, validate_package)`
   ([`eutl_scraper/publish/data_package.py`](../eutl_scraper/publish/data_package.py)). Reads the
   extracted parquet and writes the data-package ZIP. See [`main_publish.py`](../main_publish.py).

> ⚠️ Publishing is **not** part of `AllDataBundle` — it is a separate function call with its own
> config model (see Publication layer below). `main_dev*.py` are throwaway dev scripts, not
> supported entry points.

### Central config: `Settings`

[`eutl_scraper/settings.py`](../eutl_scraper/settings.py) — `Settings(dir_data=..., manual_files=...)`
is passed to every bundle and pipeline. It is the single source of truth for **where data lives**;
never construct paths manually.

- `settings.fp(key, directory, ending="csv")` — path to a framework-managed file. `key` is looked up
  in `Settings.FILENAMES`; `directory` is `settings.dir_source` (raw) or `settings.dir_extracted`
  (cleaned). Extract/augment outputs use `ending="parquet"`; raw downloads stay `csv`.
- `settings.fp_manual(key)` — path to a **user-supplied** file declared in `manual_files`. Allowed
  keys are enumerated in `Settings.MANUAL_FILES`; an unknown key raises `ValueError`.

`dir_source` (`<dir_data>/source`) and `dir_extracted` (`<dir_data>/extracted`) are created
automatically on construction.

The same file contains `DownloadClient`, an `httpx`-based client with automatic byte-range resume on
dropped connections.

### Data flow

```
[remote sources] → dir_source/ (raw CSVs) → dir_extracted/ (cleaned parquet) → data package ZIP
```

### Pipeline / Bundle model

The runtime model is two small ABCs in [`eutl_scraper/pipeline/`](../eutl_scraper/pipeline/):

- **`Pipeline`** ([`pipeline.py`](../eutl_scraper/pipeline/pipeline.py)) — one cohesive unit of work.
  Concrete `run()` calls three abstract phases in fixed order: `load` (fetch and/or read) →
  `transform` (produce output; identity allowed for fetch-only steps) → `save` (write to disk).
  Subclasses declare a class-level `name` and resolve paths via `self.settings.fp(...)`.
- **`Bundle`** ([`bundle.py`](../eutl_scraper/pipeline/bundle.py)) — a named, **flat** `list[Pipeline]`
  run in order. A Bundle never contains another Bundle; coarser bundles compose finer ones by
  *flattening* their `.pipelines` list at construction (`*FinerBundle(settings).pipelines`). There is
  no dependency resolution or topological sort — order is explicit. See
  [ADR 0001](../.ai-context/adrs/0001-bundle-is-not-a-pipeline.md) for why Bundle is not a Pipeline.

Any bundle can be run on its own (e.g. `ComplianceBundle(settings).run()`) to produce just its slice.

### Bundle composition

`AllDataBundle` flattens four source-level bundles:

| Bundle | Module | What it produces |
|---|---|---|
| `EUTLBundle` | [`eutl_scraper/eutl/`](../eutl_scraper/eutl/) | Core EUTL tables (fetch + extract + augment) |
| `EEXAuctionsBundle` | [`eutl_scraper/other/eex_auctions/`](../eutl_scraper/other/eex_auctions/) | EUA primary auction prices/volumes from EEX |
| `NaceFromLeakageListsBundle` | [`eutl_scraper/other/nace_codes/`](../eutl_scraper/other/nace_codes/) | NACE codes from bundled leakage-list Excel files |
| `InstallationLocationsBundle` | [`eutl_scraper/other/locations/`](../eutl_scraper/other/locations/) | Geocoded installation coordinates |

`EUTLBundle` ([`eutl/bundle.py`](../eutl_scraper/eutl/bundle.py)) in turn flattens per-entity bundles
(`ComplianceBundle`, `TransactionsBundle`, `AccountsBundle`, `InstallationsBundle`,
`AccountHoldersBundle`) followed by two cross-entity augment pipelines:

- `CreateETS2InstallationsPipeline` — detects installations present in compliance but missing from
  the installations table and creates stub rows tagged `ets_id="ETS2"`.
- `AddMissingAccountsFromTransactionsPipeline` — scans transaction parties for `account_id`s absent
  from the accounts table and appends them with limited metadata.

Each per-entity module (e.g. [`eutl/compliance.py`](../eutl_scraper/eutl/compliance.py)) typically
holds a `Fetch*Pipeline` (download raw CSV to `dir_source`), an `Extract*Pipeline`
(read → clean/rename → validate uniqueness → write parquet to `dir_extracted`), and the `*Bundle`
that wires them in order.

### Manual files

Two artefacts cannot be downloaded automatically and are supplied via `Settings(manual_files=...)`:

- `manual_accounts` — PowerBI accounts export (XLSX). **Required** by `AccountHoldersBundle` for
  holder identity data the public Azure blob does not expose.
- `existing_installation_locations` — optional user-maintained CSV cache of already-geocoded
  coordinates (needs `installation_id` + `source` columns); suppresses redundant geocoding calls.

### Key identifiers

- `account_id` = `"{registry_code}_{account_identifier}"` (e.g. `"DE_12345"`)
- `installation_id` = `"{registry_code}_{installation_identifier}"` (e.g. `"DE_98765"`)
- `registry_id` = two-letter country code; mapping in
  [`eutl_scraper/eutl/mappings.py`](../eutl_scraper/eutl/mappings.py)

### Publication layer (`eutl_scraper/publish/`)

`TABLE_REGISTRY` ([`table_registry.py`](../eutl_scraper/publish/table_registry.py)) maps each output
table to a `BaseConfig` subclass ([`configs.py`](../eutl_scraper/publish/configs.py),
[`configs_additional_data.py`](../eutl_scraper/publish/configs_additional_data.py)). Each config holds:

- `column_mapping`: extracted → published column renaming
- `type_convertors`: per-column callables applied before renaming
- `transformers`: additional DataFrame transforms
- `schema_path`: YAML schema under `publish/schemas/` (Frictionless field descriptors)
- `resource_metadata`: title/description/sources attached to the Frictionless `Resource`

`publish_data_package()` reads each extracted parquet, runs it through `prepare_table()` and
`create_resource()` (validates against the YAML schema), then `create_data_package()` writes the
CSVs plus `datapackage.yaml`/`.json` into a ZIP. Package-level license (CC-BY-4.0), citation,
contributors, and a general source-attribution description are set in
[`resources.py`](../eutl_scraper/publish/resources.py); per-resource source attribution is appended
automatically from each config's `resource_metadata.sources`.

> ⚠️ **Two-stage renaming.** Columns are renamed once in the extract pipeline and *again* in the
> publish config, and some names are reused/inverted across the two stages (e.g. published
> `allocated` ← extract `allocated_total`, published `allocated_free` ← extract `allocated` in
> compliance). When touching either layer, check the *other* layer's mapping before assuming a column
> name means what it says.

To add a new output table: create a `BaseConfig` subclass, add a YAML schema under
`publish/schemas/`, register it in `TABLE_REGISTRY`, and add the path to `data_paths` in
`publish_data_package()`.

### NACE codes pipeline

Uses two static Excel leakage lists (`leakage_2015.xlsx`, `leakage_2020.xlsx`) and an HTML NACE
scheme file, all bundled in `eutl_scraper/other/nace_codes/`. No downloads required.

### Geocoding pipeline

`InstallationLocationsBundle` geocodes installation addresses. Pass
`api_keys={"geoapify": "<key>", ...}` to `AllDataBundle`/`InstallationLocationsBundle`; valid service
keys are `googlemaps`, `geoapify`, `osm` (for OSM the value is a user-agent string). Services run in
parallel (one thread each). Activity types 10 (aircraft), 50 (shipping), and NA are skipped. When an
existing-locations cache is registered, API calls are suppressed **per service** for already-cached
`installation_id`s. The `max_installations` cap (applied after the activity-type filter) is available
for local testing.
