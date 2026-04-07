"""This module contains the main functions for the EUTL scraper. It provides
functions to download, extract and normalize the EUTL dataset as provided by
by the European Commission: https://union-registry-data.ec.europa.eu/report/welcome
"""

from enum import StrEnum
from pathlib import Path

from eutl_scraper.settings import (
    DIR_EXTRACTED,
    DIR_NORMALIZED,
    DIR_SOURCE,
    DIR_SOURCE_AUTOMATIC,
)

from .download import download_all_data
from .extract import extract_all_data
from .normalize import normalize_all_data


class EUTLPipelineSteps(StrEnum):
    DOWNLOAD = "download"
    EXTRACT = "extract"


def eutl_pipeline(
    dir_out: str | Path | None = None,
    steps: list[EUTLPipelineSteps] | None = None,
    fn_manual_accounts: str | Path | None = None,
) -> None:
    """Download all EUTL datasets: accounts, compliance, installations, and
    transactions and save the normalized data to the specified output directory.

    Args:
        dir_out (str | Path | None): Directory to save the downloaded data.
            If None, the default directory will be used (./data/source/automatic).
        fn_manual_accounts (str | Path | None): Filename of the manually downloaded
            account data.
            If None, an error is raised in the extraction step.
        steps (list[EUTLPipelineSteps] | None): List of pipeline steps to execute.
            If None, all steps will be executed. Possible values are:
            - EUTLPipelineSteps.DOWNLOAD: Download the data, normalized them
                and save the normalized data.
            - EUTLPipelineSteps.EXTRACT: Only extract the data from the downloaded
                files. Data will be read from the normalized directory and
                saved to the given output directory.
                This step requires the normalized data to be present in the normalized
                directory. To extract account holders, also the manually downloaded
                account data are needed.
                Note that the extraction step requires the normalized data to be
                present in the normalized directory.


    """
    # set the default output directory if not provided
    if dir_out is None:
        dir_out = DIR_EXTRACTED
    dir_out = Path(dir_out)

    # pipeline steps
    if steps is None:
        steps = list(EUTLPipelineSteps)

    if EUTLPipelineSteps.DOWNLOAD in steps:
        download_all_data(dir_out=DIR_SOURCE_AUTOMATIC)
        normalize_all_data(dir_in=DIR_SOURCE_AUTOMATIC, dir_out=DIR_NORMALIZED)

    if EUTLPipelineSteps.EXTRACT in steps:
        if fn_manual_accounts is None:
            raise ValueError(
                "fn_manual_accounts must be provided for account holder extraction."
            )
        extract_all_data(
            dir_in=DIR_NORMALIZED,
            dir_out=dir_out,
            dir_source=DIR_SOURCE,
            fn_manual_accounts=fn_manual_accounts,
        )
