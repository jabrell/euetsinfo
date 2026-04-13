"""Account holders are parties that are responsible for operating accounts.
While holders are an official entity in the EUTL system, data for holders are not
directly. In this module we therefore extract account holders from

1. Transaction data (automatically downloaded)
2. Manual account data downloaded as provided by the Power BI interface

We extract the holders, assign a unique ID, and relate account holders to
accounts. The unique ID is created in a way to be stable across time, to avoid
problems with future additions of accounts.

Note that holder creation is based on source data, i.e., data that just have been
downloaded from the EUTL system but no further processing has been done.
"""

import hashlib
import re
from pathlib import Path

import pandas as pd
from loguru import logger

from eutl_scraper.settings import Settings

from ..mappings import map_registryCode_inv


def generate_account_holder_id(row: pd.Series, digits: int = 10) -> str:
    """Generate a unique account holder ID based on available information.

    Args:
        row (pd.Series): A row from the dataframe the function is applied to
        digits (int): Number of digits to use for the hash ID (default: 10)

    Returns:
        str: A stable hash-based unique identifier for the account holder.
    """
    # 1. normalized the account holder name
    name = str(row["accountHolderName"]).strip().lower()

    # 2. Check of company registration number exists
    raw_crn = str(row["companyRegistrationNumber"]).strip().lower()

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


def _load_accounts_from_manual_data(fn_manual_account_data: Path) -> pd.DataFrame:
    """Get all accounts from manual account data

    Args:
        fn_manual_account_data (Path): Manual account data as downloaded from the
            Power BI interface
    """
    df_bi = (
        pd.read_excel(
            fn_manual_account_data,
            skipfooter=2,
            engine="calamine",
            na_values=["-"],
            keep_default_na=True,
        )
        .rename(columns={"..1": "registry_id"})
        .drop(columns=".")
        .assign(
            account_id=lambda df: (
                df["registry_id"] + "_" + df["Account Identifier"].astype(str)
            ),
        )
    )
    return df_bi


def _get_holders_from_manual_data(fn_manual_account_data: Path) -> pd.DataFrame:
    """Extract account holders from manual account data.

    Args:
        fn_manual_account_data (Path): Manual account data as downloaded from the
            EUTL system.

    Returns:
        pd.DataFrame: DataFrame of unique account holders with generated holder IDs.
    """
    df_bi = _load_accounts_from_manual_data(fn_manual_account_data)
    bi_holder_cols = {
        "Account Holder Name": "accountHolderName",
        "Company Registration No": "companyRegistrationNumber",
        "Legal Entity Identifier": "legalEntityIdentifier",
        "Main Address Line": "addressMain",
        "City": "city",
        "Telephone 1": "telephone1",
        "Telephone 2": "telephone2",
        "Email": "email",
    }
    df_bi = (
        df_bi[["account_id"] + list(bi_holder_cols.keys())]
        # drop holder if the name is missing
        .loc[lambda df: pd.notnull(df["Account Holder Name"])]
        # exclude accounts that are already in the transaction holders
        .rename(columns=bi_holder_cols)
    )
    return df_bi


def _load_accounts_from_transactions(fn_transactions: Path) -> pd.DataFrame:
    """Get all accounts from transaction data

    Args:
        fn_transactions (Path): Transaction data as automatically downloaded
    """
    df_trans = pd.read_csv(fn_transactions, low_memory=False)

    # extract transferring and acquiring accounts
    lst_df = []
    for prefix in ["TRANSFERRING", "ACQUIRING"]:
        cols = [c for c in df_trans.columns if c.startswith(prefix)]
        df_ = df_trans[cols].copy()
        cols = [c.replace(f"{prefix}_", "") for c in cols]
        df_.columns = cols
        lst_df.append(df_)

    # combine the data frames and de-duplicate
    df_trans = pd.concat(lst_df, axis=0).drop_duplicates().reset_index(drop=True)

    # add the correct registry_id and subsequently the account_id
    def assign_account_id(row) -> str:
        """Create account id from transaction accounts"""
        if pd.notnull(row["ACCOUNT_IDENTIFIER"]):
            if pd.notnull(row["registry_id"]):
                registry_id = row["registry_id"]
            else:
                registry_id = "UNKNOWN"
            return registry_id + "_" + str(int(row["ACCOUNT_IDENTIFIER"]))

    df_trans = df_trans.assign(
        registry_id=lambda df: df["REGISTRY_NAME"]
        .str.strip()
        .map(map_registryCode_inv),
        account_id=lambda df: df.apply(assign_account_id, axis=1),
    )
    return df_trans
    #     .assign(
    #         registry_id=lambda df: (
    #             df["REGISTRY_NAME"].str.strip().map(map_registry_names)
    #         ),
    #         account_id=lambda df: df.apply(assign_account_id, axis=1),
    #     )
    # )


def _get_holders_from_transactions(fn_transactions: Path) -> pd.DataFrame:
    """Extract account holders from transaction data. We only extract holders for
    accounts for which the account holder name is available, as this is needed
    for the generation of the unique holder ID.

    Args:
        fn_transactions (Path): Transaction data as automatically downloaded

    Returns:
        pd.DataFrame: DataFrame of unique account holders with generated holder IDs.
    """
    df_trans = _load_accounts_from_transactions(fn_transactions)
    trans_holder_cols = {
        "ACCOUNT_HOLDER": "accountHolderName",
        "ACCOUNT_HOLDER_COMPANY_REGISTRATION_NUMBER": "companyRegistrationNumber",
        "ACCOUNT_HOLDER_LEI": "legalEntityIdentifier",
        "ACCOUNT_HOLDER_ADDRESS1": "addressMain",
        "ACCOUNT_HOLDER_ADDRESS2": "addressSecondary",
        "ACCOUNT_HOLDER_POSTAL_CODE": "postalCode",
        "ACCOUNT_HOLDER_CITY": "city",
        "ACCOUNT_HOLDER_COUNTRY_CODE": "country",
    }
    df_trans = (
        df_trans[["account_id"] + list(trans_holder_cols.keys())]
        # drop holder if the name is missing
        .loc[lambda df: pd.notnull(df["ACCOUNT_HOLDER"])]
        .rename(columns=trans_holder_cols)
    )
    return df_trans


def extract_account_holders(
    settings: Settings, fn_manual_account_data: Path, save_to_disk: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the transaction and manual account data, which are used for holder
    extraction.

    Args:
        settings (Settings): Settings object containing directory paths and filenames.
        fn_manual_account_data (Path): Path to the manual account data Excel file.
        save_to_disk (bool): Whether to save the extracted account holders to disk.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing the account holders
            DataFrame and the link accounts holders DataFrame.
    """
    logger.info("Extracting account holders...", filter="eutl_extract")
    df_holder_trans = _get_holders_from_transactions(
        fn_transactions=settings.fp("transactions", settings.dir_source)
    ).assign(holder_id=lambda df: df.apply(generate_account_holder_id, axis=1))
    df_holder_manual = (
        _get_holders_from_manual_data(fn_manual_account_data=fn_manual_account_data)
        # exclude accounts that are already in the transaction holders
        .loc[lambda df: ~df["account_id"].isin(df_holder_trans["account_id"])]
        .assign(holder_id=lambda df: df.apply(generate_account_holder_id, axis=1))
    )
    # combine sources and de-duplicate based on account_id and holder_id
    df_holders = (
        pd.concat([df_holder_trans, df_holder_manual], axis=0)
        .drop_duplicates(subset=["account_id", "holder_id"])
        .reset_index(drop=True)
    )

    # get the link and the holders only tables
    df_link_accounts_holders = df_holders[["account_id", "holder_id"]]
    df_holders = df_holders.drop_duplicates(subset=["holder_id"]).drop(
        columns=["account_id"]
    )

    # save if output directory is given
    if save_to_disk:
        logger.info(
            "Saving extracted account holders and link accounts holders to disk...",
            filter="eutl_extract",
        )
        df_link_accounts_holders.to_csv(
            settings.fp("link_accounts_holders", settings.dir_extracted), index=False
        )
        df_holders.to_csv(
            settings.fp("account_holders", settings.dir_extracted), index=False
        )

    return df_holders, df_link_accounts_holders
