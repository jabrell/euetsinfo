import pandas as pd

from eutl_scraper.eutl.extract_new.utils import _strip_str
from eutl_scraper.settings import Settings


def _clean_and_create_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw compliance data and create unique installation IDs.

    Args:
        df (pd.DataFrame): DataFrame containing raw compliance data.
    Returns:
        pd.DataFrame: DataFrame containing normalized compliance data.
    """
    df_ = _strip_str(df).assign(
        account_id=lambda df: (
            df["REGISTRY_CODE"] + "_" + df["ACCOUNT_IDENTIFIER"].astype(str)
        ),
    )
    return df_


def _rename_and_check(df: pd.DataFrame) -> pd.DataFrame:
    """Unify account data from different sources into a single DataFrame.

    Args:
        df_direct (pd.DataFrame): DataFrame containing account data from direct
            download.

    Returns:
        pd.DataFrame: Unified DataFrame containing account data from all sources.
    """
    # 1. create the basic table from direct download
    cols = {
        "account_id": "account_id",
        "registry_code": "registry_id",
        "ACCOUNT_NAME": "accountName",
        "OPEN_DATE": "openingDate",
        "END_OF_VALIDITY_DATE": "closingDate",
        "IS_CLOSURE_PENDING": "isClosurePending",
        "SNAPSHOT_DATE": "snapshotDate",
    }
    df_accounts = df.rename(columns=cols).drop(
        columns=["REGISTRY_NAME", "ACCOUNT_IDENTIFIER", "REGISTRY_CODE"]
    )

    # 2. Make a consistent account type column
    df_accounts = df_accounts.assign(
        account_type=(lambda df: df["ETS_ACCOUNT_TYPE"].combine_first(df["FULL_TYPE"]))
    ).drop(columns=["ETS_ACCOUNT_TYPE", "FULL_TYPE", "ACCOUNT_TYPE"])

    # 3. convert is closure pending to boolean
    df_accounts = df_accounts.assign(
        isClosurePending=lambda df: df["isClosurePending"] == "Y"
    )
    return df_accounts


def extract_accounts(settings: Settings, save_to_disk: bool = True) -> pd.DataFrame:
    """Create a unified account DataFrame from the raw data.

    Args:
        settings (Settings): Settings object containing configuration.
        save_to_disk (bool): Whether to save the extracted data to disk.
            Defaults to True.

    Returns:
        pd.DataFrame: Unified DataFrame containing account data from all sources.
    """
    df = (
        pd.read_csv(settings.fp("accounts", settings.dir_source))
        .pipe(_clean_and_create_ids)
        .pipe(_rename_and_check)
    )
    if save_to_disk:
        df.to_csv(settings.fp("accounts", settings.dir_extracted), index=False)
    return df
