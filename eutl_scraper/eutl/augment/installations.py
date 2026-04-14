import pandas as pd
from loguru import logger

from eutl_scraper.settings import Settings


def create_ets2_installations(settings: Settings) -> pd.DataFrame | None:
    """Some installations are in the compliance table but not listed in the
    installations table. We create these accounts under the assumption that
    these are ETS2 installations.

    Args:
        settings (Settings): Settings object containing configuration.

    Returns:
        pd.DataFrame | None: DataFrame containing the missing installations, or
            None if there are no missing installations or if there was an error.
    """
    df_compliance = pd.read_csv(settings.fp("compliance", settings.dir_extracted))

    df_installations = pd.read_csv(settings.fp("installations", settings.dir_extracted))
    missing_installations = set(df_compliance["installation_id"].unique()) - set(
        df_installations["installation_id"].unique()
    )

    # should only have a few missing installations
    if len(missing_installations) > 30:
        logger.error(
            f"Found {len(missing_installations)} missing installations in compliance "
            "table. This is more than expected. Cannot create missing installations."
        )
        return

    if missing_installations:
        logger.info(
            f"Found {len(missing_installations)} missing installations. "
            "Assume these are ETS2 installations and adding them to the installations"
            " table."
        )
        cols = ["installation_id", "installation_name", "registry_id", "registry_name"]
        df_missing = (
            df_compliance[df_compliance["installation_id"].isin(missing_installations)]
            .loc[:, cols]
            .drop_duplicates()
            .assign(
                ets_id="ETS2",
            )
        )
        # installation_id should be unique
        if not df_missing["installation_id"].is_unique:
            logger.error(
                "Installation IDs are not unique in the missing installations. "
                "Cannot create missing installations."
            )
            return
        # append the missing installations to the installations table
        df_installations = pd.concat(
            [df_installations, df_missing], ignore_index=True
        ).assign(
            created_at=lambda df: df.created_at.ffill(),
        )
        df_installations.to_csv(
            settings.fp("installations", settings.dir_extracted), index=False
        )
        return df_missing
    return
