# Parquet for dir_extracted, csv kept in dir_source

The new pipeline abstraction in `eutl_scraper/pipeline/` writes every product it places in `dir_extracted` as parquet (snappy, single file per entity, `pd.to_parquet(path)` with no extra args). Callers opt in per-call via the existing `settings.fp(key, dir_extracted, ending="parquet")` — no new helper method. `dir_source` stays verbatim upstream bytes (csv stays csv, xlsx stays xlsx, zip stays zip) so it remains a forensic snapshot of what we received. Legacy pipelines that still read/write csv from `dir_extracted` are left untouched; the publish layer continues to read csv and will be migrated only once every entity has moved to the new pipelines.

## Considered and rejected

- **Parquet in `dir_source` too.** Rejected: several sources are non-tabular (Excel, ZIP, HTML), and re-encoding tabular sources would mean `dir_source` no longer holds "what upstream sent us," weakening its value when diagnosing upstream changes. The speed win is small because each source is read at most once per run.
- **Dedicated `settings.fp_extracted(key)` helper that bakes in `.parquet`.** Rejected: would interfere with legacy callers that still expect csv from the same directory, and is less flexible if an entity later wants a different ending.
- **Partition transactions from day one.** Rejected as YAGNI. No concrete filter workload is documented yet, and row-group pushdown on a single parquet file is already a large win over csv. Partitioning turns the product into a directory, which complicates `fp`'s file-path contract — defer until a real query pattern motivates it.
- **Enforce dtype contracts in each extract pipeline.** Rejected: the Frictionless schemas in `publish/schemas/` are the natural contract holder and already run in publish. Adding a second enforcement layer in extract is premature; new augment pipelines will be built directly against parquet's real dtypes, and that is the point of doing the parquet switch before migrating augments.

## Consequences

- New pipelines and legacy pipelines coexist in `dir_extracted` under different extensions (`eutl_accounts.parquet` vs `eutl_accounts.csv`). No collision, but two artifacts for any entity in mid-migration.
- The publish layer is temporarily not a usable consumer of new-pipeline output. Until publish is migrated, new pipelines are exercised end-to-end only via augments and ad-hoc analysis.
- Future migration of publish (separate ADR) will need to decide on parquet-only vs parquet-preferred-with-csv-fallback.
