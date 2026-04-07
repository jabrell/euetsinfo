"""This module contains the main functions for the EUTL scraper. It provides
functions to download, extract and normalize the EUTL dataset as provided by
by the European Commission: https://union-registry-data.ec.europa.eu/report/welcome
"""

from pathlib import Path

from eutl_scraper.settings import DIR_SOURCE_AUTOMATIC

from .download import download_all_data


def eutl_pipeline(dir_out: str | Path | None = None) -> None:
    """Download all EUTL datasets: accounts, compliance, installations, and
    transactions and save the normalized data to the specified output directory.

    Args:
        dir_out (str | Path | None): Directory to save the downloaded data.
            If None, the default directory will be used (./data/source/automatic).
    """
    if dir_out is None:
        dir_out = DIR_SOURCE_AUTOMATIC
    dir_out = Path(dir_out)
    download_all_data(dir_out=dir_out)
