"""Module for downloading EUTL data from specified URLs. This module
provides functions to download datasets related to accounts, compliance,
installations, and transactions. The data can be saved locally as CSV files
for further processing. The module currently only supports download of the
data given under the "download data" section but not from the PowerBi app itself.
"""

import zipfile

import httpx
import pandas as pd
from loguru import logger

from eutl_scraper.settings import DownloadClient, Settings

URL_SOURCE = {
    "accounts": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/account/accounts_daily.csv.gz",
    "installations": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operator/operators_daily.csv.gz",
    "compliance": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operators_yearly_activity/operators_yearly_activity_daily.csv.gz",
}
URL_TRANSACTIONS = "https://climate.ec.europa.eu/document/download/0cda99f1-16f6-41e7-b190-887cd71339a4_en?filename=transactions_eutl_2024_0.zip"


def _download_csv(
    key: str, fn_out: str | None = None, client: DownloadClient | None = None
) -> pd.DataFrame:
    """Download a CSV file corresponding to the given key.

     The key is used to look up the URL in the URL_SOURCE dictionary. The file is
     downloaded using the provided client or a default DownloadClient if none is
     provided.

     Args:
        key (str): Key for the dataset to download. Must be one of the keys in
            URL_SOURCE.
        fn_out (str | None, optional): Output filename to save the data. Defaults to
            None.
        client (DownloadClient | None, optional): HTTP client to use for downloading

    Returns:
        pd.DataFrame: DataFrame containing the downloaded data.
    """
    url = URL_SOURCE.get(key)
    if url is None:
        raise ValueError(
            f"Invalid key '{key}'. Valid keys are: {list(URL_SOURCE.keys())}"
        )
    client = client or DownloadClient()
    logger.info(f"Downloading {key} data...", filter="eutl_download")
    df = client.download_csv(url=url, fn_out=fn_out)
    return df


def download_transactions(
    url: str | None = None,
    fn_out: str | None = None,
    client: DownloadClient | httpx.Client | None = None,
) -> pd.DataFrame:
    """Download transaction data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing transaction data.
    """
    url = url or URL_TRANSACTIONS
    client = client or DownloadClient()
    logger.info("Downloading transactions data...", filter="eutl_download")
    # Download the zip file to memory
    zip_content = client.download_with_resume(url=url)
    # Extract the CSV file that starts with "transactions_EUTL_PUBLIC_NOTESD"
    with zipfile.ZipFile(zip_content) as zf:
        csv_filename = [
            name
            for name in zf.namelist()
            if name.startswith("transactions_EUTL_PUBLIC_NOTESD")
        ][0]
        with zf.open(csv_filename) as csv_file:
            df = pd.read_csv(csv_file, low_memory=False)
    if fn_out is not None:
        df.to_csv(fn_out, index=False)
    return df


def download_all(settings: Settings) -> None:
    """Download all datasets:
    accounts, compliance, installations, and transactions.

    Args:
        settings (Settings): The settings object containing configuration values.
    """
    with DownloadClient() as client:
        for key in URL_SOURCE.keys():
            _download_csv(
                key=key, fn_out=settings.fp(key, settings.dir_source), client=client
            )
        download_transactions(
            fn_out=settings.fp("transactions", settings.dir_source), client=client
        )
