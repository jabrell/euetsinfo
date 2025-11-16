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

url_source = {
    "accounts": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/account/accounts_daily.csv.gz",
    "installations": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operator/operators_daily.csv.gz",
    "compliance": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operators_yearly_activity/operators_yearly_activity_daily.csv.gz",
    "transactions": "https://climate.ec.europa.eu/document/download/0cda99f1-16f6-41e7-b190-887cd71339a4_en?filename=transactions_eutl_2024_0.zip",
}


def _download_data(url: str, fn_out: str | None = None) -> pd.DataFrame:
    """Download data from the given URL.

    Args:
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


def accounts(url: str | None = None, fn_out: str | None = None) -> pd.DataFrame:
    """Extract account data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to extract data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing account data.
    """
    if url is None:
        url = url_source["accounts"]
    df = _download_data(url, fn_out)
    return df


def compliance(url: str | None = None, fn_out: str | None = None) -> pd.DataFrame:
    """Download compliance data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing compliance data.
    """
    if url is None:
        url = url_source["compliance"]
    df = _download_data(url, fn_out)
    return df


def installations(url: str | None = None, fn_out: str | None = None) -> pd.DataFrame:
    """Download installation data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing installation data.
    """
    if url is None:
        url = url_source["installations"]
    df = _download_data(url, fn_out)
    return df


def transactions(url: str | None = None, fn_out: str | None = None) -> pd.DataFrame:
    """Download transaction data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to download data from. Defaults to None.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing transaction data.
    """
    if url is None:
        url = url_source["transactions"]

    # Download the zip file to memory
    response = httpx.get(url_source["transactions"])
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


def all_data(dir_out: str) -> None:
    """Download all datasets:
    accounts, compliance, installations, and transactions.

    Args:
        dir_out (str): Directory to save the downloaded datasets.
    """
    accounts(
        fn_out=f"{dir_out}/eutl_accounts.csv",
    )
    compliance(
        fn_out=f"{dir_out}/eutl_compliance.csv",
    )
    installations(
        fn_out=f"{dir_out}/eutl_installations.csv",
    )
    transactions(
        fn_out=f"{dir_out}/eutl_transactions.csv",
    )
