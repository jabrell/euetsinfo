"""Extract account and account holder information from data.

Account data is available from three different locations:
- Direct download from the EUTL website
- Extracted from the Power BI datasets
- Extracted from the transactions dataset

The main source is the direct download. However, the direct download does not
provided information for the holders. Thus we extract the holder information from
the transaction and power BI datasets as well.

# TODO: Some accounts are only in the transaction (about 600). These are accounts
that are not registered in the EU systems, mainly Switzerland, UK, as well as
accounts to import international credits. These are not handled so far.
"""

import hashlib
import re
from pathlib import Path

import pandas as pd


def load_account_data(
    fn_direct: str | Path,
    fn_bi: str | Path,
    fn_trans: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load account data from multiple sources into DataFrames.

    Args:
        fn_direct (str | Path): File path for direct download CSV.
        fn_bi (str | Path): File path for BI Excel
        fn_trans (str | Path): File path for transaction data CSV

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            DataFrames for direct, BI, and transaction account data.
    """
    # get automatically downloaded account data
    df_direct = pd.read_csv(fn_direct).assign(
        account_id=lambda df: df["REGISTRY_CODE"]
        + "_"
        + df["ACCOUNT_IDENTIFIER"].astype(str),
    )

    # create mapping of registry names to codes
    map_registry_names = df_direct.set_index("REGISTRY_NAME")["REGISTRY_CODE"].to_dict()
    map_registry_names.update({"Switzerland": "CH", "CDM": "CDM"})

    # extract account data from BI download
    df_bi = (
        pd.read_excel(
            fn_bi,
            skipfooter=2,
            engine="calamine",
            na_values=["-"],
            keep_default_na=True,
        )
        .rename(columns={"..1": "registry_id"})
        .drop(columns=".")
        .assign(
            account_id=lambda df: df["registry_id"]
            + "_"
            + df["Account Identifier"].astype(str),
        )
    )

    # extract account data from transactions
    def assign_account_id(row) -> str:
        if pd.notnull(row["ACCOUNT_IDENTIFIER"]):
            if pd.notnull(row["registry_id"]):
                registry_id = row["registry_id"]
            else:
                registry_id = "UNKNOWN"
            return registry_id + "_" + str(int(row["ACCOUNT_IDENTIFIER"]))

    df_trans = pd.read_csv(fn_trans, low_memory=False)
    lst_df = []
    for prefix in ["TRANSFERRING", "ACQUIRING"]:
        cols = [c for c in df_trans.columns if c.startswith(prefix)]
        df_ = df_trans[cols].copy()
        cols = [c.replace(f"{prefix}_", "") for c in cols]
        df_.columns = cols
        lst_df.append(df_)
    df_trans = (
        pd.concat(lst_df, axis=0)
        .drop_duplicates()
        .reset_index(drop=True)
        .assign(
            registry_id=lambda df: df["REGISTRY_NAME"]
            .str.strip()
            .map(map_registry_names),
            account_id=lambda df: df.apply(assign_account_id, axis=1),
        )
    )

    return df_direct, df_bi, df_trans


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


def extract_holders(
    df_trans: pd.DataFrame, df_bi: pd.DataFrame, digits: int = 10
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract unique account holders from transaction data. Holders are only extracted
        if they account holder name is available. We extract first from the
        transaction data, as they have more complete holder information. Afterwards,
        we fill in missing holders from the BI data. The holder IDs are generated
        using a stable hash-based method based on account holder name and company
        registration number.

    Args:
        df_trans: DataFrame containing accounts from the transaction data.
        df_bi: DataFrame containing accounts from the BI data.
        digits: Number of digits to use for the hash ID (default: 10)

    Returns:

        A tuple containing two DataFrames:
            - DataFrame of unique account holders with generated holder IDs.
            - DataFrame of accounts IDs with associated holder IDs.
    """
    # 1. Extract holders from transaction data
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
    df_holder_trans = (
        df_trans[["account_id"] + list(trans_holder_cols.keys())]
        # drop holder if the name is missing
        .loc[lambda df: pd.notnull(df["ACCOUNT_HOLDER"])]
        .rename(columns=trans_holder_cols)
        # assign unique id
        .assign(
            holder_id=lambda df: df.apply(generate_account_holder_id, axis=1),
        )
    )
    # determine the accounts linked to each holder
    df_holder_trans = df_holder_trans.drop_duplicates(subset=["holder_id"])

    # 2. Extract holders from BI data
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
    df_holder_bi = (
        df_bi[["account_id"] + list(bi_holder_cols.keys())]
        # drop holder if the name is missing
        .loc[lambda df: pd.notnull(df["Account Holder Name"])]
        # exclude accounts that are already in the transaction holders
        .loc[lambda df: ~df["account_id"].isin(df_holder_trans["account_id"])]
        .rename(columns=bi_holder_cols)
        # assign unique id
        .assign(
            holder_id=lambda df: df.apply(generate_account_holder_id, axis=1),
        )
    )

    # 3. combine both holder dataframes, drop duplicates and create account-holder
    # mapping
    df_holder = pd.concat([df_holder_bi, df_holder_trans], axis=0)
    df_link_account_holder = df_holder[["holder_id", "account_id"]].drop_duplicates()
    df_holder = df_holder.drop_duplicates(subset=["holder_id"]).drop(
        columns=["account_id"]
    )

    return df_holder.reset_index(drop=True), df_link_account_holder.reset_index(
        drop=True
    )


def create_basic_account_table(
    df_direct: pd.DataFrame,
) -> pd.DataFrame:
    """Unify account data from different sources into a single DataFrame.

    Args:
        df_direct (pd.DataFrame): DataFrame containing account data from direct download.

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
    df_accounts = df_direct.rename(columns=cols).drop(
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


def create_account_table_with_holders(
    fn_direct: str | Path,
    fn_bi: str | Path,
    fn_trans: str | Path,
    dir_out: str | Path | None = None,
    digits: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create unified account and account holder tables from multiple data sources.

    Args:
        fn_direct (str | Path): File path for direct download CSV.
        fn_bi (str | Path): File path for BI Excel
        fn_trans (str | Path): File path for transaction data CSV
        dir_out (str | Path, optional): Output directory to save the resulting CSVs.
            If not provided, the CSVs are not saved. Defaults to None.
        digits (int): Number of digits to use for the hash ID (default: 10)

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
            DataFrames for unified accounts, account holders, and account-holder links.
            Note that the account table already contains the holder IDs.
    """
    # 1. load and prepare the data
    df_direct, df_bi, df_trans = load_account_data(
        fn_direct=fn_direct,
        fn_bi=fn_bi,
        fn_trans=fn_trans,
    )

    # 2. create the basic account table
    df_accounts = create_basic_account_table(df_direct)

    # 3. extract account holders
    df_holders, df_link_account_holder = extract_holders(
        df_trans=df_trans, df_bi=df_bi, digits=digits
    )

    # add the account holder IDs to the account table
    assert df_link_account_holder["account_id"].is_unique, (
        "Account IDs in link table are not unique"
    )

    df_accounts = df_accounts.merge(df_link_account_holder, on="account_id", how="left")

    # 4. save to CSVs (if desired)
    if dir_out is not None:
        dir_out = Path(dir_out)
        dir_out.mkdir(parents=True, exist_ok=True)

        fn_accounts = dir_out / "eutl_accounts.csv"
        fn_holders = dir_out / "eutl_account_holders.csv"
        fn_links = dir_out / "eutl_account_holder_links.csv"

        df_accounts.to_csv(fn_accounts, index=False)
        df_holders.to_csv(fn_holders, index=False)
        df_link_account_holder.to_csv(fn_links, index=False)

    return df_accounts, df_holders, df_link_account_holder
