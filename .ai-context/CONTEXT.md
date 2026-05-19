# EUTL Scraper — Pipeline Architecture

Shared language for the pipeline abstraction being formalised in `eutl_scraper/pipeline/`. Captures how we talk about pipelines, steps, and how they compose.

## Language

**Pipeline**:
A unit of data processing with three fixed phases — `load`, `transform`, `save` — that produces one coherent product.
_Avoid_: job, task, script, workflow (those are coarser concepts; see **Bundle**).

**Phase**:
One of the three fixed stages inside a pipeline: **Load**, **Transform**, **Save**. Every pipeline has exactly these three; none are optional in shape (a phase may be identity, but it always exists).
_Avoid_: step, stage (overloaded with Dagster terminology).

**Load**:
The phase that brings input data into memory. May fetch from a remote source, read from local disk (`dir_source` or `dir_extracted`), or both. Where the data live on disk is governed by `Settings`; where they live remotely is the pipeline's own responsibility.

**Transform**:
The phase that turns inputs into the pipeline's product. Identity is allowed (e.g. a fetch pipeline that just persists raw bytes).

**Save**:
The phase that writes the product to disk. May produce multiple files — the constraint is "one cohesive product," not "one file."

**Product**:
The coherent output of a single pipeline. Examples: "the raw EUTL accounts CSV," "the cleaned installations table," "the four gzipped raw files from the EUTL Azure blob." Always declared up-front; may span multiple files.

**Fetch Pipeline**:
A pipeline whose **Load** reaches a remote source and whose **Save** writes to `dir_source`. Its **Transform** may be identity (raw passthrough) or non-trivial (unzip a transactions archive, decompress gzip, drop sentinel rows). One fetch pipeline corresponds to one source operation and may produce multiple files.

**Extract Pipeline**:
A pipeline whose **Load** reads only from `dir_source` (no remote calls) and whose **Save** writes to `dir_extracted`. Produces one logical entity (e.g. accounts, installations, account_holders). May have multi-input load (e.g. account holders reads the manual Excel plus the accounts raw file).

**Augment Pipeline**:
A pipeline whose **Load** reads from `dir_extracted` (multiple entities allowed), whose **Transform** combines them, and whose **Save** writes back to `dir_extracted` — typically overwriting one of the inputs. The ETS2-stubs and missing-accounts-from-transactions work are augment pipelines.
_Note_: "augment" is no longer a phase inside a larger pipeline — it is a pipeline of its own. It is **not** a special "depends on previous steps" construct; its dependency on prior outputs is just "my load reads files from `dir_extracted`" — the same kind of disk-based dependency an Extract Pipeline has on `dir_source`.

**Bundle**:
A named collection of pipelines grouped by **source/domain** (EUTL, EEX, NACE, Geocoding). Two responsibilities:
1. **Factory** — accepts source-level runtime config (API keys, user-supplied file paths, knobs like `max_installations`) and uses it to decide *which* pipelines to instantiate. E.g. the geocoding bundle includes `GeoapifyPipeline` only if a Geoapify key is provided.
2. **Runner** — `Bundle.run()` is `for p in self.pipelines: p.run()` in declared list order, nothing more.
Source-level runtime config (API keys, manually-downloaded file paths) enters the system via the Bundle's constructor. Per-pipeline disk paths still come from **Settings**.
_Not a Pipeline_: a Bundle does not have load/transform/save; it only has `run()`. The shared interface with Pipeline is `run()` and nothing else (Composite pattern, not inheritance).
_Avoid_: pipeline-of-pipelines, meta-pipeline.

**Kind**:
A tag on each Pipeline — one of `Fetch | Extract | Augment` — used **only** as a user-facing filter (e.g. `bundle.run(kinds={Augment})` to re-run only augment pipelines during development). The Kind has no role in dependency resolution or execution ordering. It exists because the current `EUTLPipelineSteps` filtering workflow needs to survive the migration.

## Relationships

- A **Pipeline** has exactly three **Phases**: Load, Transform, Save.
- A **Pipeline** produces exactly one **Product** (which may span multiple files).
- A **Bundle** groups multiple **Pipelines** and defines their execution order.
- **Fetch / Extract / Augment Pipelines** are kinds of Pipeline, distinguished by *where their Load reads from* and *where their Save writes to*:
  - Fetch: remote → `dir_source`
  - Extract: `dir_source` → `dir_extracted`
  - Augment: `dir_extracted` → `dir_extracted`
- Cross-entity work (ETS2 stubs, missing accounts) is modelled as an **Augment Pipeline**, never as a phase inside another pipeline.

## Flagged ambiguities

- "Pipeline" in the current code (`pipeline_eutl`) means what we now call a **Bundle**. The new `BasePipeline` ABC in `eutl_scraper/pipeline/__init__.py` will mean a single load/transform/save unit. Existing call sites will need renaming during migration.
- "Bundle" vs "Job" vs "Group" — provisional; revisit when composition semantics (Question 3) are resolved.
- "Step" is deliberately not used. The proposal's `EUTLPipelineSteps` enum (download / extract / augment) is really a *phase-filter over a bundle*, not a property of any one pipeline.
