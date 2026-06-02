# Publishing

The publication layer turns the cleaned parquet tables in
`Settings.dir_extracted` into a
[Frictionless Data Package](https://specs.frictionlessdata.io/) — a ZIP
bundle of CSV files with a machine-readable `datapackage.{yaml,json}`
descriptor. The entry point is
[`publish_data_package`][eutl_scraper.publish.data_package.publish_data_package].

## The flow

For each table in the registry:

```
parquet (dir_extracted)
   │
   ▼
prepare_table       ← apply type converters + transformers + column rename
   │
   ▼
create_resource     ← wrap as Frictionless Resource, attach metadata,
   │                  validate against YAML schema
   ▼
create_data_package ← collect resources, write CSVs + descriptor, zip
   │
   ▼
my_data_package.zip
```

Each step is documented in the
[publish API reference](../api/publish.md).

## The registry

[`TABLE_REGISTRY`][eutl_scraper.publish.table_registry]
maps a table name to an instantiated
[`BaseConfig`][eutl_scraper.publish.configs.BaseConfig] subclass. The
config carries everything the publication layer needs for one output
table:

| Field | Purpose |
| --- | --- |
| `name` | The published table name; also used as the CSV filename. |
| `schema_path` | Path to the YAML Frictionless schema in `publish/schemas/`. |
| `resource_metadata` | Title, description, upstream sources, encoding. |
| `column_mapping` | Raw column name → published column name. Selection happens here too — only mapped columns appear in the output. |
| `type_convertors` | Column-level callables (e.g. parse dates, cast to `Int64`). Applied to the raw source columns *before* renaming. |
| `transformers` | DataFrame-level callables for row-shape changes (drop nulls, drop duplicates). |

`BaseConfig` provides factory helpers — `_to_datetime`,
`_to_nullable_int`, `_dropna_subset`, `_format_nace`,
`_drop_duplicates_subset` — that concrete configs use to stay
declarative.

## Schemas

YAML schemas live in
[`eutl_scraper/publish/schemas/`](https://github.com/jabrell/eutl_scraper_v2/tree/main/eutl_scraper/publish/schemas).
They describe the published fields in Frictionless field-descriptor
form: name, type, format, constraints, foreign-key relationships, and
documentation strings. Adding a new table requires adding a YAML file
here; the config references it via `schema_path`.

## Validation

Two validation passes are available:

- **Per-resource** — runs unconditionally inside
  [`create_resource`][eutl_scraper.publish.resources.create_resource]
  on up to `max_valid_rows` rows of each table. A validation failure
  raises and aborts the publication run. This is the gate that prevents
  a broken table from ever appearing in a package.
- **Whole-package** — optional, controlled by the `validate_package`
  flag on
  [`publish_data_package`][eutl_scraper.publish.data_package.publish_data_package].
  When enabled, Frictionless re-validates the zipped package end-to-end
  (including cross-resource foreign keys) and the resulting
  `Report` is returned alongside the `Package` object.

## Adding a new published table

1. Subclass `BaseConfig` (in `configs.py` or `configs_additional_data.py`),
   set `name`, `schema_path`, `resource_metadata`, `column_mapping`, and
   any `type_convertors` / `transformers` needed in `__post_init__`.
2. Add the corresponding YAML schema under `publish/schemas/`.
3. Register the config in `TABLE_REGISTRY` under the same name.
4. Add an entry to the `data_paths` dictionary in
   `publish_data_package` so the layer knows which extracted file to
   read.

For the full step-by-step contributor flow — including how to wire the
upstream pipeline that *produces* the new parquet file — see
[Onboarding new data](onboarding.md).
