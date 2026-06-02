# Architecture overview

The scraper is built around two small abstractions: a **pipeline** is a
single unit of data work, and a **bundle** is a named, ordered list of
pipelines. Everything else — the EUTL crawl, the auxiliary data sources,
the publication step — is expressed by composing these two primitives.

## Pipelines

A [`Pipeline`][eutl_scraper.pipeline.pipeline.Pipeline] performs three
fixed phases, in order:

1. **`load`** — bring inputs into memory (remote fetch, local read, or
   both).
2. **`transform`** — turn those inputs into the pipeline's output.
3. **`save`** — persist the output to disk.

Each pipeline produces exactly one cohesive output. The output may
span multiple files, but conceptually it is one thing — one cleaned
table, one downloaded archive, one geocoded result set. The phases are
abstract methods; `Pipeline.run` is concrete and always calls them in
order, so subclasses cannot reorder or skip a phase.

All disk paths are resolved through
[`Settings.fp`][eutl_scraper.settings.Settings.fp], never by string
concatenation. See [Settings and paths](settings.md) for the rationale.

## Bundles

A [`Bundle`][eutl_scraper.pipeline.bundle.Bundle] is a named, **flat**
ordered list of pipelines. Running a bundle runs its pipelines in the
declared order. There is no dependency resolution and no topological
sort — the order is whatever the bundle's `_build_pipelines` method
returns.

Bundles compose by **flattening**. A coarser bundle does not nest a
finer bundle as a child object; instead, it splats the finer bundle's
`.pipelines` attribute into its own list:

```python
class EUTLBundle(Bundle):
    name = "eutl"

    def _build_pipelines(self):
        return [
            *ComplianceBundle(self.settings).pipelines,
            *TransactionsBundle(self.settings).pipelines,
            # ...
            CreateETS2InstallationsPipeline(self.settings),
        ]
```

The runtime model of every bundle — coarse or fine — is the same: a flat
`list[Pipeline]`. Nesting exists only at construction time as a
convenience for *building* the list. A user who wants to run just one
slice can instantiate the finer bundle directly and call `.run()`.

## A light DAG analogy

If a directed acyclic graph helps you think about this, a pipeline is a
**node** and a bundle is a **subgraph**: a labelled, ordered traversal
of nodes. Coarser bundles are subgraphs that contain other subgraphs and
loose nodes — bundles of bundles and pipelines. Important caveat: the
scraper does **not** infer execution order from data dependencies. The
order is declared by the author of `_build_pipelines`, and the runtime
simply iterates the resulting flat list.

## User input

Most pipelines need only a [`Settings`][eutl_scraper.settings.Settings]
object. Bundles that need runtime knobs accept them as keyword arguments
on `__init__` and pass them through to their pipelines. The top-level
[`AllDataBundle`][eutl_scraper.bundles.AllDataBundle] is the canonical
example:

```python
AllDataBundle(
    settings=Settings(dir_data=Path("./data"), manual_files={...}),
    api_keys={"geoapify": "..."},
    max_installations=None,
)
```

Two channels carry user input:

- **Code-level config** — API keys, integer knobs, paths — flows through
  bundle constructors.
- **Manual files** — artefacts the framework cannot download
  automatically (e.g. a PowerBI XLSX export, a cached geocoding result
  set) — are registered on `Settings` via the `manual_files` argument
  and looked up by pipelines through
  [`Settings.fp_manual`][eutl_scraper.settings.Settings.fp_manual].

## Putting it together

A typical run constructs `Settings`, then `AllDataBundle`, then calls
`.run()`. The bundle internally flattens four sub-bundles into one
sequential list of pipelines and executes them in declared order. The
publication step (see [Publishing](publishing.md)) reads the resulting
extracted tables and produces a Frictionless Data Package.

For a worked composition example, see the
[`EUTLBundle`][eutl_scraper.eutl.bundle.EUTLBundle] reference, whose
docstring enumerates the seven-step execution order it imposes on its
per-entity sub-bundles.
