"""Pipeline and Bundle abstractions.

Core building blocks every data flow in this project is built on:

- `Pipeline` — a single `load` → `transform` → `save` unit producing one
  cohesive output.
- `Bundle` — a named, flat list of `Pipeline` instances run in order; the
  source-level entry point for runtime config (API keys, manual file
  paths, knobs).

See [`pipeline.pipeline`][eutl_scraper.pipeline.pipeline] and
[`pipeline.bundle`][eutl_scraper.pipeline.bundle] for the abstractions.
"""

from .bundle import Bundle
from .pipeline import Pipeline

__all__ = ["Bundle", "Pipeline"]
