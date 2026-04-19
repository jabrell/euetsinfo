"""We construct the accounts given in the transaction data or in the
data downloaded from power bi and add them to the accounts data frame. This
ensures referential integrity
"""

import pandas as pd
from loguru import logger

from eutl_scraper.eutl.mappings import map_registryCode_inv
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


def get_transaction_parties(df: pd.DataFrame) -> pd.DataFrame:
    """Get transaction parties from the transactions data.

    Args:
        df (pd.DataFrame): DataFrame with transactions data.

    Returns:
        pd.DataFrame: DataFrame with transaction parties."""
    prefixes = ["TRANSFERRING", "ACQUIRING"]
    lst_df = []
    for prefix in prefixes:
        map_cols = {
            f"{prefix}_REGISTRY_NAME": "registryName",
            f"{prefix}_ACCOUNT_TYPE1": "account_type1",
            f"{prefix}_ACCOUNT_TYPE2": "account_type2",
            f"{prefix}_ACCOUNT_TYPE3": "account_type3",
            f"{prefix}_ACCOUNT_OPEN_DT": "openingDate",
            f"{prefix}_ACCOUNT_END_OF_VALIDITY": "closingDate",
            f"{prefix}_ACCOUNT_NAME": "accountName",
            f"{prefix}_ACCOUNT_IDENTIFIER": "account_identifier",
            f"{prefix}_ACCOUNT_HOLDER": "account_holder_name",
            f"{prefix}_ACCOUNT_HOLDER_ADDRESS1": "account_holder_address1",
            f"{prefix}_ACCOUNT_HOLDER_ADDRESS2": "account_holder_address2",
            f"{prefix}_ACCOUNT_HOLDER_CITY": "account_holder_city",
            f"{prefix}_ACCOUNT_HOLDER_POSTAL_CODE": "account_holder_postal_code",
            f"{prefix}_ACCOUNT_HOLDER_COUNTRY_CODE": "account_holder_country_code",
            f"{prefix}_ACCOUNT_HOLDER_COMPANY_REGISTRATION_NUMBER": (
                "account_holder_company_registration_number"
            ),
            f"{prefix}_ACCOUNT_HOLDER_LEI": "account_holder_lei",
        }
        df_ = (
            df[list(map_cols.keys())]
            .rename(columns=map_cols)
            .assign(
                registry_id=lambda x: (
                    x["registryName"].str.strip().map(map_registryCode_inv)
                ),
            )
        )
        lst_df.append(df_)
    df_trans_accounts = (
        pd.concat(lst_df, ignore_index=True)
        .dropna(subset=["account_identifier"])
        .assign(
            account_identifier=lambda df: df["account_identifier"].astype("int64"),
            account_id=lambda df: df.apply(_form_account_account_id, axis=1),
        )
        .drop_duplicates()
    )
    assert df_trans_accounts.account_id.is_unique, "account_id is not unique"
    return df_trans_accounts


def add_missing_accounts_from_transactions(
    settings: Settings, append_to_existing: bool = True
) -> pd.DataFrame:
    """Add missing accounts from transaction parties to accounts DataFrame.

    Args:
        settings (Settings): Settings object with file paths and other configurations.
        append_to_existing (bool, optional): Whether to append missing accounts
            to existing accounts.
            Defaults to True.

    Returns:
        pd.DataFrame: DataFrame with missing accounts added.
    """
    logger.info("Adding missing accounts from transactions...", filter="eutl_pipeline")

    # load the data
    df_trans = pd.read_csv(
        settings.fp("transactions", settings.dir_source), low_memory=False
    )
    df_accounts = pd.read_csv(settings.fp("accounts", settings.dir_extracted))

    # get transaction parties
    df_transaction_parties = get_transaction_parties(df_trans)

    def _format_account_type(x: str) -> str:
        """Format account type by taking the last part after splitting by underscore.

        Args:
            x (str): Account type string.

        Returns:
            str: Formatted account type string."""
        if x == "-":
            return pd.NA
        return x.split("-")[-1]

    ids_transaction_parties = set(df_transaction_parties.account_id)
    ids_accounts_extracted = set(df_accounts.account_id)
    missing_accounts = ids_transaction_parties - ids_accounts_extracted
    df_missing_parties = df_transaction_parties[
        df_transaction_parties.account_id.isin(missing_accounts)
    ]
    cols = ["accountName", "openingDate", "closingDate", "account_id", "account_type2"]
    print(f"Missing accounts: {len(df_missing_parties)}")
    df_missing_accounts = (
        df_missing_parties[cols]
        .assign(
            accountName=lambda df: df["accountName"].fillna("NotKnown"),
            account_type=lambda df: df["account_type2"].map(_format_account_type),
            isClosurePending=pd.NA,
            snapshotDate=lambda df: df_accounts.snapshotDate.unique()[0],
            created_at=lambda df: df_accounts.created_at.unique()[0],
        )
        .drop(columns=["account_type2"])
    )
    df_all_accounts = pd.concat([df_accounts, df_missing_accounts], ignore_index=True)
    if append_to_existing:
        fn_out = settings.fp("accounts", settings.dir_extracted)
        df_all_accounts.to_csv(fn_out, index=False)
    return df_all_accounts
