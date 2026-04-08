"""Module to fetch coordinates for EUTL installations based on the
[Geoapify API](https://www.geoapify.com/).

The first version of this module was provided by: Roberto Rossini (Bruegel)"""

from pathlib import Path

import pandas as pd

from ..settings import DIR_EXTRACTED
from .fetch_coordinates import geocode_installations, load_installations

__all__ = [
    "geocode_installations",
    "load_installations",
    "pipeline_installation_coordinates",
]


def pipeline_installation_coordinates(
    api_key: str,
    fn_installations: str | Path | None = None,
    dir_out: Path | None = None,
    rate_limit_seconds: float = 0.25,
    max_installations: int | None = None,
) -> pd.DataFrame:
    """Download coordinates for all installations in the EUTL dataset.

    Args:
        api_key: API key for the geocoding service
            Geoapify API key: https://www.geoapify.com/
        fn_installations: Path to the CSV file containing the installations data.
            Path to file with the installation.
            If None, the default path will be used
            (./data/extracted/eutl_installations.csv).
        dir_out: Directory to save the output CSV file for the geocoded data.
            If None, the default directory will be used
            (./data/extracted).
        rate_limit_seconds: Number of seconds to wait between API calls to respect
            rate limits.
        max_installations: Optional limit on the number of installations to process
            (useful for testing). If None, all installations will be processed.

    Returns:
        A DataFrame with the coordinates for all installations.
    """
    # default settings if not provided
    # installation file
    if fn_installations is None:
        fn_installations = DIR_EXTRACTED / "eutl_installations.csv"
    else:
        fn_installations = Path(fn_installations)

    # get and prepare the installation file
    df_inst = load_installations(input_csv=fn_installations)

    # fetch coordinates and save to disk
    df = geocode_installations(
        df=df_inst,
        api_key=api_key,
        rate_limit_seconds=rate_limit_seconds,
        max_installations=max_installations,
    )

    # save to disk
    if dir_out is not None:
        dir_out = Path(dir_out)
        fn_out = dir_out / "installation_locations.csv"
        df.to_csv(fn_out, index=False)
    df.to_csv(fn_out, index=False)

    return df
