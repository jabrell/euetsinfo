"""This module contains the main functions for the EUTL scraper. It provides
functions to download, extract and normalize the EUTL dataset as provided by
by the European Commission: https://union-registry-data.ec.europa.eu/report/welcome
"""

from enum import StrEnum
from pathlib import Path

from eutl_scraper.settings import Settings

from .download import download_all_data
from .extract_new import extract_all


class EUTLPipelineSteps(StrEnum):
    DOWNLOAD = "download"
    EXTRACT = "extract"


def pipeline_eutl(
    settings: Settings,
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
    # pipeline steps
    if steps is None:
        steps = list(EUTLPipelineSteps)

    if EUTLPipelineSteps.DOWNLOAD in steps:
        print("Download EUTL data...")
        download_all_data(settings=settings)

    if EUTLPipelineSteps.EXTRACT in steps:
        if fn_manual_accounts is None:
            raise ValueError(
                "fn_manual_accounts must be provided for account holder extraction."
            )
        print("Extract EUTL data...")
        extract_all(
            settings=settings,
            fn_manual_account_data=fn_manual_accounts,
        )
