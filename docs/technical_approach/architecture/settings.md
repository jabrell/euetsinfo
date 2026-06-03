# Settings and paths

[`Settings`][eutl_scraper.settings.Settings] is the single source of
truth for **where data lives** on disk. It is constructed once at the
start of a run and threaded through every pipeline and bundle. No
pipeline ever constructs a file path by string concatenation; all paths
are resolved through `Settings`.

## On-disk layout

Under a single root `dir_data`, two stage directories are created
automatically:

- **`dir_source`** (`<dir_data>/source`) — raw artefacts as they arrive
  from a remote source or as supplied by the user. The input directory
  for extract pipelines.
- **`dir_extracted`** (`<dir_data>/extracted`) — cleaned, normalised
  tables ready for publication. The output directory for extract and
  augment pipelines and the input directory for the publication layer.

The data flow between them is:

```
[remote sources] → dir_source/ → dir_extracted/ → data package ZIP
```

## Stable internal names

The class-level `Settings.FILENAMES` dictionary maps an **internal key**
(e.g. `"accounts"`, `"compliance"`) to a **stable basename** (e.g.
`"eutl_accounts"`). Pipelines refer to files by internal key only; the
basename is private to `Settings`. Adding a new artefact means adding a
single entry here, after which every producer and consumer can find it
via [`Settings.fp`][eutl_scraper.settings.Settings.fp]:

```python
settings = Settings(dir_data=Path("./data"))
settings.fp("accounts", settings.dir_source)        # raw download
settings.fp("accounts", settings.dir_extracted, ending="parquet")
```

## Manual files

Some entities depend on artefacts the framework cannot download
automatically — the user exports them by hand or maintains them as a
local cache. The class-level `Settings.MANUAL_FILES` dictionary is the
allow-list of accepted manual-file keys. The user provides the actual
external paths at construction time via the `manual_files` argument;
pipelines retrieve them through
[`Settings.fp_manual`][eutl_scraper.settings.Settings.fp_manual]:

```python
Settings(
    dir_data=Path("./data"),
    manual_files={
        "manual_accounts": Path("manual_data/accounts_20260412.xlsx"),
        "existing_installation_locations": Path(
            "manual_data/installation_locations.csv"
        ),
    },
)
```

Currently registered:

- **`manual_accounts`** — PowerBI accounts export (XLSX). Required by
  the account holders bundle; the public Azure blob does not expose this
  data.
- **`existing_installation_locations`** — optional cache of
  previously-geocoded coordinates; suppresses redundant Geoapify calls.

Unknown keys raise `ValueError` at construction. This prevents
typos from silently disabling a dependent pipeline.

## HTTP downloads

[`DownloadClient`][eutl_scraper.settings.DownloadClient] is a small
`httpx`-based client used by fetch pipelines. It supports byte-range
resume on dropped connections, which matters for the multi-gigabyte
transactions archive.

## Why route everything through `Settings`?

Because the on-disk layout is the only piece of state shared across
every pipeline. Centralising it means renames, new stages, or
relocations are one-file changes. A pipeline that constructs paths
inline is one rename away from breaking the next pipeline that consumes
its output.

See the [Settings API reference](../api/settings.md) for the full method
signatures and the complete `FILENAMES` / `MANUAL_FILES` listings.
