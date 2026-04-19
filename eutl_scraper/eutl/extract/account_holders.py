import hashlib
import re
from pathlib import Path

import pandas as pd
from loguru import logger

from eutl_scraper.settings import Settings


def _form_account_account_id(row: pd.Series) -> str:
    """Form account_id from registry_id and account_identifier.

    Args:
        row (pd.Series): Row of the DataFrame with registry_id and account_identifier.

    Returns:
        str: Formed account_id.
    """
    if pd.isnull(row["account_identifier"]):
        return row["account_identifier"]
    return f"{row['registry_id']}_{int(row['account_identifier'])}"


def load_accounts_power_bi_download(fn_bi_account_data: Path) -> pd.DataFrame:
    """Load accounts data from the Power BI download.

    Args:
        fn_bi_account_data (Path): Account data as downloaded from the
            Power BI interface
    """
    map_cols = {
        "Account Identifier": "account_identifier",
        "National Administrator": "national_administrator",
        "Account Type": "account_type",
        "Account Holder Name": "account_holder_name",
        "Account Name": "accountName",
        "Company Registration No": "account_holder_company_registration_number",
        "Main Address Line": "account_holder_address1",
        "City": "account_holder_city",
        "Legal Entity Identifier": "account_holder_lei",
        "..1": "registry_id",
        "account_id": "account_id",
    }
    df_bi = (
        pd.read_excel(
            fn_bi_account_data,
            skipfooter=2,
            engine="calamine",
            na_values=["-"],
            keep_default_na=True,
        )
        .rename(columns=map_cols)
        .assign(
            account_id=lambda df: df.apply(_form_account_account_id, axis=1),
            account_holder_name=lambda df: (
                df["account_holder_name"].fillna("unknown").str.strip()
            ),
        )[list(map_cols.values())]
    )
    return df_bi


def generate_account_holder_id(row: pd.Series, digits: int = 10) -> str:
    """Generate a unique account holder ID based on available information.

    Args:
        row (pd.Series): A row from the dataframe the function is applied to
        digits (int): Number of digits to use for the hash ID (default: 10)

    Returns:
        str: A stable hash-based unique identifier for the account holder.
    """
    # 1. normalized the account holder name
    name = str(row["account_holder_name"]).strip().lower()

    # 2. Check of company registration number exists
    raw_crn = str(row["account_holder_company_registration_number"]).strip().lower()

    is_missing = (
        pd.isnull(raw_crn)
        or raw_crn in ["", "nan", "none", "null"]
        or re.match(r"^0+$", raw_crn)
        or re.match(r"^-+$", raw_crn)
    )

    crn = "no_crn" if is_missing else raw_crn

    # 3. Create composite ID string
    composite_id = f"{name}|{crn}"

    # 4. Generate stable hash-based ID
    hash = hashlib.sha256(composite_id.encode()).hexdigest()

    return hash[:digits]


def extract_account_holders_from_power_bi_download(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """We construct the account holders out of the manual downloads from the
    Power BI interface. We checked that the account holders in the transactions data
    are all present in the account holders data from the Power BI download. The
    exception are accounts involved in transactions that are also not present in
    the standard account data. These are accounts in foreign countries (GB, CH, CDM....)

    Args:
        df (pd.DataFrame): Account data as downloaded from the Power BI interface.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: Extracted account holders and link table.
    """
    # create the holder id
    df_ = df.assign(
        account_holder_id=lambda df: df.apply(generate_account_holder_id, axis=1)
    )

    # extract the link between accounts and account holders
    df_link_accounts_holders = df_[["account_id", "account_holder_id"]].assign(
        created_at=pd.Timestamp.now()
    )
    assert df_link_accounts_holders.account_id.is_unique, (
        "account_id is not unique in link table"
    )
    df_link_accounts_holders.info()

    # create the account holders table
    df_account_holders = (
        df_.drop(columns=["account_id", "accountName"])
        .drop_duplicates(subset=["account_holder_id"])
        .assign(
            created_at=pd.Timestamp.now(),
        )
    )
    return df_account_holders, df_link_accounts_holders


def extract_account_holders(
    settings: Settings, fn_manual_account_data: Path, save_to_disk: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract account holders from data obtained from the Power Bi interface.
    Note that the data are obtained using all account and not just the
    operator holding accounts.

    Args:
        settings (Settings): Settings object containing directory paths and filenames.
        fn_manual_account_data (Path): Path to the manual account data Excel file.
        save_to_disk (bool): Whether to save the extracted account holders to disk.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing the account holders
            DataFrame and the link accounts holders DataFrame.
    """
    logger.info(
        "Extracting account holders from Power BI download...", filter="eutl_extract"
    )
    df_bi = load_accounts_power_bi_download(fn_manual_account_data)
    df_holders, df_link_accounts_holders = (
        extract_account_holders_from_power_bi_download(df_bi)
    )

    # save if output directory is given
    if save_to_disk:
        logger.info(
            "Saving extracted account holders and link accounts holders to disk...",
            filter="eutl_extract",
        )
        df_link_accounts_holders.to_csv(
            settings.fp("link_account_holder", settings.dir_extracted), index=False
        )
        df_holders.to_csv(
            settings.fp("account_holders", settings.dir_extracted), index=False
        )

    return df_holders, df_link_accounts_holders
