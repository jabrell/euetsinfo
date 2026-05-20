# Onboarding new data

This page summarises the steps needed to bring a new dataset into the
scraper. It assumes familiarity with the
[Architecture overview](index.md), [Settings](settings.md), and
[Publishing](publishing.md). Two granularities are covered:

- **Path A** — adding a pipeline to an existing bundle (a new variant
  of an entity that is already handled, or a derived table built from
  existing extracts).
- **Path B** — adding a whole new bundle (a new top-level data source).

In both cases publication is optional: if the new table is for internal
consumption only, skip the publication steps.

## Path A — new pipeline in an existing bundle

1. **Implement the pipeline.** Subclass
   [`Pipeline`][eutl_scraper.pipeline.pipeline.Pipeline] in the
   appropriate subpackage (e.g. `eutl_scraper/eutl/` or
   `eutl_scraper/other/<source>/`). Declare `name` at class level and
   implement `load`, `transform`, `save`. Resolve all paths through
   [`Settings.fp`][eutl_scraper.settings.Settings.fp] / `fp_manual`.

2. **Register filenames.** If the pipeline writes a new artefact, add
   its internal key and stable basename to `Settings.FILENAMES`. Every
   downstream consumer reads through this key.

3. **Append to the bundle.** Edit the relevant bundle's
   `_build_pipelines` to include the new pipeline in the correct
   position. Order is significant — augment pipelines must run after the
   extract pipelines they depend on.

4. **Publish (optional).** If the new table is part of the data
   package:
   - Subclass [`BaseConfig`][eutl_scraper.publish.configs.BaseConfig]
     for the new table (column mapping, type converters, resource
     metadata).
   - Add a YAML schema under `eutl_scraper/publish/schemas/`.
   - Register the config in
     [`TABLE_REGISTRY`][eutl_scraper.publish.table_registry] (see the
     `table_registry` module).
   - Add an entry to the `data_paths` dictionary in
     [`publish_data_package`][eutl_scraper.publish.data_package.publish_data_package].

## Path B — new top-level bundle

1. **Decide the boundary.** A bundle should correspond to one external
   source (one website, one API, one set of files). Pick a short
   `name` that will appear in logs.

2. **Implement the bundle.** Subclass
   [`Bundle`][eutl_scraper.pipeline.bundle.Bundle] in
   `eutl_scraper/other/<source>/`. Implement `_build_pipelines` to
   return the pipelines in execution order. If the bundle needs runtime
   config (API keys, knobs), accept it as keyword arguments in
   `__init__`, store on `self`, then call `super().__init__(settings)`.

3. **Handle user input, if any.**
   - **Code-level knobs and API keys** are accepted by the bundle's
     `__init__` and threaded down to the relevant pipelines, following
     the `InstallationLocationsBundle` pattern visible in
     [`AllDataBundle`][eutl_scraper.bundles.AllDataBundle].
   - **Manual files** require adding a key to
     `Settings.MANUAL_FILES` (with a one-line description) and reading
     it via
     [`Settings.fp_manual`][eutl_scraper.settings.Settings.fp_manual]
     inside the pipeline.

4. **Compose into `AllDataBundle`.** In
   [`eutl_scraper/bundles.py`](https://github.com/jabrell/eutl_scraper_v2/blob/main/eutl_scraper/bundles.py),
   splat the new bundle's `.pipelines` into the list returned by
   `AllDataBundle._build_pipelines`. Pass any required runtime config.
   Remember: composition is by flattening; `AllDataBundle` does not hold
   a reference to your bundle, only to its pipelines.

5. **Publish (optional).** As in Path A — `BaseConfig` subclass, YAML
   schema, registry entry, `data_paths` entry.

## Sanity checks before committing

- The bundle runs in isolation: `MyBundle(settings).run()` succeeds on a
  clean `dir_data`.
- The new parquet files appear under `dir_extracted` with the basenames
  declared in `Settings.FILENAMES`.
- If publication was added: `publish_data_package(settings, fn_out,
  validate_package=True)` succeeds and the resulting ZIP contains the
  new CSV.
- `uv run ruff check .` and `uv run ruff format .` are clean.

For the underlying API contracts, refer to the
[Pipelines and bundles API reference](../api/pipeline.md) and the
[publish API reference](../api/publish.md).
