"""This module contains the main functions for the EUTL scraper. It provides
functions to download, extract and normalize the EUTL dataset as provided by
by the European Commission: https://union-registry-data.ec.europa.eu/report/welcome
"""

from enum import StrEnum
from pathlib import Path

from loguru import logger

from eutl_scraper.eutl.augment.installations import create_ets2_installations
from eutl_scraper.settings import Settings

from .download import download_all
from .extract import extract_all


class EUTLPipelineSteps(StrEnum):
    DOWNLOAD = "download"
    EXTRACT = "extract"
    AUGMENT = "augment"


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
            - EUTLPipelineSteps.AUGMENT: Augment the data with additional information.
                This step requires the extracted data to be present in the extracted
                directory.
    """
    # pipeline steps
    if steps is None:
        steps = list(EUTLPipelineSteps)

    if EUTLPipelineSteps.DOWNLOAD in steps:
        logger.info("Download EUTL data...", filter="eutl_pipeline")
        download_all(settings=settings)

    if EUTLPipelineSteps.EXTRACT in steps:
        if fn_manual_accounts is None:
            raise ValueError(
                "fn_manual_accounts must be provided for account holder extraction."
            )
        logger.info("Extract EUTL data...", filter="eutl_pipeline")
        extract_all(
            settings=settings,
            fn_manual_account_data=fn_manual_accounts,
        )

    if EUTLPipelineSteps.AUGMENT in steps:
        logger.info("Augment EUTL data...", filter="eutl_pipeline")
        create_ets2_installations(settings=settings)
