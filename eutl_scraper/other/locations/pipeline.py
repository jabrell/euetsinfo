"""Module to fetch coordinates for EUTL installations based on the
[Geoapify API](https://www.geoapify.com/).

The first version of this module was provided by: Roberto Rossini (Bruegel)"""

import pandas as pd
from loguru import logger

from ...settings import Settings
from .fetch_coordinates import geocode_installations, load_installations


def pipeline_installation_coordinates(
    settings: Settings,
    api_key: str,
    save_to_disk: bool = True,
    rate_limit_seconds: float = 0.25,
    max_installations: int | None = None,
) -> pd.DataFrame:
    """Download coordinates for all installations in the EUTL dataset.

    Args:
        api_key: API key for the geocoding service
            Geoapify API key: https://www.geoapify.com/
        save_to_disk (bool): Whether to save the extracted data to disk.
            Defaults to True.
        rate_limit_seconds: Number of seconds to wait between API calls to respect
            rate limits.
        max_installations: Optional limit on the number of installations to process
            (useful for testing). If None, all installations will be processed.

    Returns:
        A DataFrame with the coordinates for all installations.
    """
    # default settings if not provided
    # installation file
    fn_installations = settings.fp("installations", settings.dir_extracted)

    # get and prepare the installation file
    df_inst = load_installations(input_csv=fn_installations)

    # fetch coordinates and save to disk
    logger.info(
        "Starting installation coordinates pipeline...",
        filter="installation_coordinates_pipeline",
    )
    df = geocode_installations(
        df=df_inst,
        api_key=api_key,
        rate_limit_seconds=rate_limit_seconds,
        max_installations=max_installations,
    )

    # save to disk
    if save_to_disk:
        logger.info(
            "Saving extracted installation coordinates to disk...",
            filter="installation_coordinates_pipeline",
        )
        fn_out = settings.fp("installation_locations", settings.dir_extracted)
        df.to_csv(fn_out, index=False)

    return df
