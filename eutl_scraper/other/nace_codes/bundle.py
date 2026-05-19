"""NACE-by-installation pipeline.

Orchestrates the existing sibling module `.nace_from_leakage_lists`:

- `extract_nace_scheme` parses the bundled NACE Rev. 2 HTML scheme.
- `extract_nace_by_installation` parses the bundled 2015 and 2020
  leakage-list Excel files, joins them with the scheme, and yields one
  row per installation with `nace_2015` / `nace_2020`.

Two classes:

- `ExtractNaceFromLeakageListsPipeline` — single pipeline producing two
  cohesive parquet products in `dir_extracted`:
  `nace_from_leakage_lists` and `nace_scheme`.
- `NaceFromLeakageListsBundle` — flat bundle of the pipeline above, with
  one source-level knob: `drop_missing_installations`.

The three input files (`leakage_2015.xlsx`, `leakage_2020.xlsx`,
`NACE_REV2_20200427_154248.htm`) live next to this file inside the
package and are not downloaded from anywhere.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import Settings

from .nace_from_leakage_lists import (
    extract_nace_by_installation,
    extract_nace_scheme,
)

MY_DIR = Path(__file__).resolve().parent
FN_LEAKAGE_2015 = MY_DIR / "leakage_2015.xlsx"
FN_LEAKAGE_2020 = MY_DIR / "leakage_2020.xlsx"
FN_NACE_SCHEME = MY_DIR / "NACE_REV2_20200427_154248.htm"


class ExtractNaceFromLeakageListsPipeline(Pipeline):
    """Build the NACE-by-installation and NACE-scheme tables from bundled inputs.

    Inputs:
        Three package-bundled files (constants `FN_LEAKAGE_2015`,
        `FN_LEAKAGE_2020`, `FN_NACE_SCHEME`) plus, when
        `drop_missing_installations=True`, the extracted installations
        parquet at
        `settings.fp("installations", settings.dir_extracted, ending="parquet")`.

    Product:
        Two cohesive tables written to `dir_extracted`:

        - **nace_from_leakage_lists** — one row per installation with
          `installation_id`, `nace_2015` and `nace_2020`.
        - **nace_scheme** — the NACE Rev. 2 classification table parsed
          from the bundled HTML.

    Output locations (both `ending="parquet"`):

    - `settings.fp("nace_from_leakage_lists", settings.dir_extracted, ...)`
    - `settings.fp("nace_scheme", settings.dir_extracted, ...)`

    Knobs:
        `drop_missing_installations` — when `True` (default), rows whose
        `installation_id` is not present in the extracted installations
        table are dropped from the NACE-by-installation product (with a
        warning). Matches the legacy default.
    """

    name = "extract_nace_from_leakage_lists"

    def __init__(self, settings: Settings, drop_missing_installations: bool = True):
        super().__init__(settings)
        self.drop_missing_installations = drop_missing_installations

    def load(self) -> None:
        self.df_nace_scheme = extract_nace_scheme(fn_in=FN_NACE_SCHEME)
        self.df_nace_by_installation = extract_nace_by_installation(
            fn_leakage_2015=FN_LEAKAGE_2015,
            fn_leakage_2020=FN_LEAKAGE_2020,
            df_nace_codes=self.df_nace_scheme,
        )
        if self.drop_missing_installations:
            self.df_installations = pd.read_parquet(
                self.settings.fp(
                    "installations", self.settings.dir_extracted, ending="parquet"
                )
            )
        else:
            self.df_installations = None

    def transform(self) -> None:
        if not self.drop_missing_installations:
            return
        known = set(self.df_installations.installation_id)
        missing = set(self.df_nace_by_installation.installation_id) - known
        if missing:
            logger.warning(
                f"Dropping {len(missing)} NACE-tagged installations not "
                "found in the EUTL installations table."
            )
            self.df_nace_by_installation = self.df_nace_by_installation[
                ~self.df_nace_by_installation.installation_id.isin(missing)
            ]

    def save(self) -> None:
        self.df_nace_by_installation.to_parquet(
            self.settings.fp(
                "nace_from_leakage_lists",
                self.settings.dir_extracted,
                ending="parquet",
            ),
            index=False,
        )
        self.df_nace_scheme.to_parquet(
            self.settings.fp(
                "nace_scheme", self.settings.dir_extracted, ending="parquet"
            ),
            index=False,
        )


class NaceFromLeakageListsBundle(Bundle):
    """NACE codes from the bundled 2015/2020 leakage lists.

    Source-level runtime config:
        `drop_missing_installations` — propagated to
        `ExtractNaceFromLeakageListsPipeline`. When `True`, the bundle
        has a hard dependency on the extracted installations parquet
        being on disk; run an upstream installations bundle first.
    """

    name = "nace_from_leakage_lists"

    def __init__(self, settings: Settings, drop_missing_installations: bool = True):
        self.drop_missing_installations = drop_missing_installations
        super().__init__(settings)

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            ExtractNaceFromLeakageListsPipeline(
                self.settings,
                drop_missing_installations=self.drop_missing_installations,
            ),
        ]
