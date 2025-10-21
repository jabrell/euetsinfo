import io
import zipfile

import httpx
import pandas as pd

from eutl_scraper.mappings import map_account_type_inv

url_source = {
    "accounts": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/account/accounts_daily.csv.gz",
    "installations": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operator/operators_daily.csv.gz",
    "compliance": "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/operators_yearly_activity/operators_yearly_activity_daily.csv.gz",
    "transactions": "https://climate.ec.europa.eu/document/download/0cda99f1-16f6-41e7-b190-887cd71339a4_en?filename=transactions_eutl_2024_0.zip",
}


def extract_accounts(url: str | None = None) -> pd.DataFrame:
    """Extract account data from the givrn URL or default URL.

    Args:
        url (str | None, optional): URL to extract data from. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing account data.
    """
    if url is None:
        url = url_source["accounts"]

    # some column renaming (mainly to lower case)
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }

    # get and do minor transformations including creating a unique account id
    df = pd.read_csv(url, compression="gzip")
    df = (
        df.assign(
            account_id=lambda df: df.REGISTRY_CODE
            + "_"
            + df.ACCOUNT_IDENTIFIER.astype(str),
            # TODO some missings here which seem to be national ETS2 accounts
            account_type_id=lambda df: (
                df.FULL_TYPE.fillna(df.ETS_ACCOUNT_TYPE).map(map_account_type_inv)
            ),
            closure_pending=lambda df: df.IS_CLOSURE_PENDING == "Y",
        )
        .drop(columns=["ACCOUNT_IDENTIFIER", "IS_CLOSURE_PENDING"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
    )
    return df


def extract_compliance(url: str | None = None) -> pd.DataFrame:
    """Extract compliance data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to extract data from. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing compliance data.
    """
    if url is None:
        url = url_source["compliance"]

    # get data and do minor transformations including creating a unique
    # installation ID
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }
    df = (
        pd.read_csv(url, compression="gzip")
        .assign(
            installation_id=lambda df: df.REGISTRY_CODE
            + "_"
            + df.INSTALLATION_IDENTIFIER.astype(str)
        )
        .drop(columns=["INSTALLATION_IDENTIFIER"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
    )
    return df


def extract_installations(url: str | None = None) -> pd.DataFrame:
    """Extract installation data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to extract data from. Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing installation data.
    """
    if url is None:
        url = url_source["installations"]

    # get data and do minor transformations including creating a unique
    # installation ID
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }
    df = (
        pd.read_csv(url, compression="gzip")
        .assign(
            installation_id=lambda df: df.REGISTRY_CODE
            + "_"
            + df.INSTALLATION_IDENTIFIER.astype(str)
        )
        .drop(columns=["INSTALLATION_IDENTIFIER"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
    )
    return df


def extract_transactions(url: str | None = None) -> pd.DataFrame:
    """Extract transaction data from the given URL or default URL.

    Args:
        url (str | None, optional): URL to extract data from. Defaults to None.

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
    return df
