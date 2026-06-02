"""Augment installations with ETS2 stubs from the compliance table.

One pipeline class:

- `CreateETS2InstallationsPipeline` — reads the extracted compliance and
  installations tables, finds `installation_id`s present in compliance
  but absent from installations, builds stub rows tagged `ets_id="ETS2"`,
  and overwrites the installations parquet file with the augmented table.
"""

import pandas as pd
from loguru import logger

from eutl_scraper.pipeline import Pipeline


class CreateETS2InstallationsPipeline(Pipeline):
    """Append ETS2-tagged stub installations inferred from compliance.

    Inputs:
        Two parquet files in `dir_extracted`:

        - `settings.fp("compliance", settings.dir_extracted, ending="parquet")`
        - `settings.fp("installations", settings.dir_extracted, ending="parquet")`

        Both must have been produced earlier (by `ComplianceBundle` and
        `InstallationsBundle`). This pipeline does no remote calls and no
        reads from `dir_source`.

    Output:
        The installations table augmented with stub rows for any
        `installation_id` that appears in compliance but not in
        installations. Stubs carry only `installation_id`,
        `installation_name`, `registry_id`, `registry_name` (taken from
        compliance) plus `ets_id="ETS2"`; all other columns are NA.
        `created_at` is forward-filled from the existing rows so the
        column type is preserved.

    Output location:
        `settings.fp("installations", settings.dir_extracted, ending="parquet")`
        — overwrites the installations file produced by
        `ExtractInstallationsPipeline`. The `link_installation_account`
        table is *not* touched.

    Failure modes (fail loud — both raise `ValueError`):

    - More than `MAX_MISSING` (30) missing installations: the legacy
      threshold for "this is no longer ETS2 — something upstream broke."
      Refuses to write.
    - Duplicate `installation_id` in the constructed stub rows.

    No-op:
        Zero missing installations is allowed and is a clean no-op — the
        existing installations file is left untouched (no rewrite).
    """

    name = "create_ets2_installations"
    MAX_MISSING = 30
    _STUB_COLUMNS = [
        "installation_id",
        "installation_name",
        "registry_id",
        "registry_name",
    ]

    def load(self) -> None:
        self.df_compliance = pd.read_parquet(
            self.settings.fp(
                "compliance", self.settings.dir_extracted, ending="parquet"
            )
        )
        self.df_installations = pd.read_parquet(
            self.settings.fp(
                "installations", self.settings.dir_extracted, ending="parquet"
            )
        )

    def transform(self) -> None:
        missing = set(self.df_compliance["installation_id"].unique()) - set(
            self.df_installations["installation_id"].unique()
        )
        if not missing:
            logger.info("No missing installations — nothing to augment.")
            self.df_augmented = None
            return
        if len(missing) > self.MAX_MISSING:
            raise ValueError(
                f"Found {len(missing)} installations in compliance but not in "
                f"installations (>{self.MAX_MISSING}). Refusing to auto-tag as "
                "ETS2 — investigate upstream."
            )
        df_missing = (
            self.df_compliance.loc[
                self.df_compliance["installation_id"].isin(missing),
                self._STUB_COLUMNS,
            ]
            .drop_duplicates()
            .assign(ets_id="ETS2")
        )
        if not df_missing["installation_id"].is_unique:
            raise ValueError(
                "Duplicate installation_id in inferred ETS2 stubs — refuse to write."
            )
        logger.info(
            f"Adding {len(df_missing)} inferred ETS2 installations to the "
            "installations table."
        )
        self.df_augmented = pd.concat(
            [self.df_installations, df_missing], ignore_index=True
        ).assign(created_at=lambda df: df.created_at.ffill())

    def save(self) -> None:
        if self.df_augmented is None:
            return
        self.df_augmented.to_parquet(
            self.settings.fp(
                "installations", self.settings.dir_extracted, ending="parquet"
            ),
            index=False,
        )
