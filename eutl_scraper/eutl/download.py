"""Module for downloading EUTL data from specified URLs. This module
provides functions to download datasets related to accounts, compliance,
installations, and transactions. The data can be saved locally as CSV files
for further processing. The module currently only supports download of the
data given under the "download data" section but not from the PowerBi app itself.
"""

import io
import zipfile

import httpx
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from eutl_scraper.settings import Settings

URL_SOURCE = {
    "accounts": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/account/accounts_daily.csv.gz",
    "installations": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operator/operators_daily.csv.gz",
    "compliance": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operators_yearly_activity/operators_yearly_activity_daily.csv.gz",
    "transactions": "https://climate.ec.europa.eu/document/download/0cda99f1-16f6-41e7-b190-887cd71339a4_en?filename=transactions_eutl_2024_0.zip",
}


def _download_data(url: str, fn_out: str | None = None) -> pd.DataFrame:
    """Download data from the given URL.

    Args:
        client (httpx.Client): HTTP client to use for downloading the data.
        url (str): URL to download data from.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing the downloaded data.
    """
    df = pd.read_csv(url, compression="gzip")
    if fn_out is not None:
        df.to_csv(fn_out, index=False)
    return df


def download_accounts(
    url: str | None = None, fn_out: str | None = None
) -> pd.DataFrame:
    """Extract account data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to extract data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing account data.
    """
    if url is None:
        url = URL_SOURCE["accounts"]
    df = _download_data(url, fn_out)
    return df


def download_compliance(
    url: str | None = None, fn_out: str | None = None
) -> pd.DataFrame:
    """Download compliance data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing compliance data.
    """
    if url is None:
        url = URL_SOURCE["compliance"]
    df = _download_data(url, fn_out)
    return df


def download_installations(
    url: str | None = None, fn_out: str | None = None
) -> pd.DataFrame:
    """Download installation data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing installation data.
    """
    if url is None:
        url = URL_SOURCE["installations"]
    df = _download_data(url, fn_out)
    return df


@retry(
    retry=retry_if_exception_type(httpx.RemoteProtocolError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=60),
    reraise=True,
)
def download_transactions(
    client: httpx.Client, url: str | None = None, fn_out: str | None = None
) -> pd.DataFrame:
    """Download transaction data from the given URL or default URL.

    Args:
        Client: httpx.Client to use for downloading the data.
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing transaction data.
    """
    if url is None:
        url = URL_SOURCE["transactions"]

    # Download the zip file to memory
    response = client.get(url)
    zip_content = io.BytesIO(response.content)

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


def download_all_data(settings: Settings) -> None:
    """Download all datasets:
    accounts, compliance, installations, and transactions.

    Args:
        settings (Settings): The settings object containing configuration values.
    """
    download_accounts(
        fn_out=settings.fp("accounts", settings.dir_source),
    )
    download_compliance(
        fn_out=settings.fp("compliance", settings.dir_source),
    )
    download_installations(
        fn_out=settings.fp("installations", settings.dir_source),
    )
    download_transactions(
        client=settings.client,
        fn_out=settings.fp("transactions", settings.dir_source),
    )
