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
    fn_out: str | Path | None = None,
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
        fn_out: Path to the output CSV file for the geocoded data.
            If None, the default path will be used
            (./data/extracted/eutl_installations_geocoded.csv).
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
    # output file for geocoded data
    if fn_out is None:
        fn_out = DIR_EXTRACTED / "installation_locations.csv"
    else:
        fn_out = Path(fn_out)

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
    df.to_csv(fn_out, index=False)

    return df
