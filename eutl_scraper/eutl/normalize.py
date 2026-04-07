"""Module for normalizing data. Normalization includes minor transformations
and standardizing column names. The main transformations are:

- Creating unique IDs for accounts and installations by combining registry codes
  with their respective identifiers.
- Renaming columns to lower case for consistency.
- Assigning a constant ETS ID to stamp the system where the data come from
- basic cleaning and type conversions."""

import warnings
from pathlib import Path

import pandas as pd

from eutl_scraper.mappings import map_account_type_inv

from .mappings import map_registryCode_inv


def _strip_str(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from string columns in the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: DataFrame with whitespace stripped from string columns.
    """
    df = df.copy()
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    df[str_cols] = df[str_cols].apply(lambda x: x.str.strip())
    return df


def normalize_compliance(
    df: pd.DataFrame, fn_out: str | Path | None = None
) -> pd.DataFrame:
    """Normalize compliance data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw compliance data.
        fn_out (str | Path | None): Optional output filename to save the normalized
            data.
    Returns:
        pd.DataFrame: DataFrame containing normalized compliance data.
    """
    # do minor transformations including creating a unique installation ID
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }
    df_c = (
        _strip_str(df)
        .assign(
            installation_id=lambda df: (
                df.REGISTRY_CODE + "_" + df.INSTALLATION_IDENTIFIER.astype(str)
            ),
            ets_id="euets",
            snapshot_date=pd.to_datetime(df.SNAPSHOT_DATE, format="%Y-%m-%d"),
        )
        .drop(columns=["INSTALLATION_IDENTIFIER"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
    )
    # clean types and missing values
    df_c = (
        df_c.replace({-1.0: pd.NA})
        .assign(
            year=lambda df: df.period_year.astype("Int64"),
            excluded=lambda df: df.excluded == "Y",
            ch_excluded=lambda df: df.ch_excluded == "Y",
        )
        .drop(columns=["period_year"])
    )
    if fn_out is not None:
        df_c.to_csv(fn_out, index=False)
    return df_c


def normalize_installations(
    df: pd.DataFrame, fn_out: str | Path | None = None
) -> pd.DataFrame:
    """Normalize installation data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw installation data.
        fn_out (str | Path | None): Optional output filename to save the normalized
            data.

    Returns:
        pd.DataFrame: DataFrame containing normalized installation data.
    """
    # do minor transformations including creating a unique installation ID
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }
    df_inst = (
        _strip_str(df)
        .assign(
            installation_id=(
                lambda df: (
                    df.REGISTRY_CODE + "_" + df.INSTALLATION_IDENTIFIER.astype(str)
                )
            ),
            account_id=(
                lambda df: (
                    df.ACCOUNT_REGISTRY_CODE + "_" + df.ACCOUNT_IDENTIFIER.astype(str)
                )
            ),
            ets_id="euets",
            snapshot_date=pd.to_datetime(df.SNAPSHOT_DATE, format="%Y-%m-%d"),
        )
        .drop(columns=["INSTALLATION_IDENTIFIER"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
    )
    if fn_out is not None:
        df_inst.to_csv(fn_out, index=False)
    return df_inst


def normalize_transactions(
    df: pd.DataFrame, fn_out: str | Path | None = None
) -> pd.DataFrame:
    """Normalize transaction data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw transaction data.
        fn_out (str | Path | None): Optional output filename to save the normalized
            data.

    Returns:
        pd.DataFrame: DataFrame containing normalized transaction data.
    """
    col_rename = {
        "ORIGINATING_REGISTRY": "originating_registry_id",
    }
    df_trans = (
        _strip_str(df)
        .assign(
            # add the registry ids
            acquiring_registry_id=(
                lambda df: df.ACQUIRING_REGISTRY_NAME.str.strip().map(
                    map_registryCode_inv
                )
            ),
            transferring_registry_id=(
                lambda df: df.TRANSFERRING_REGISTRY_NAME.str.strip().map(
                    map_registryCode_inv
                )
            ),
            ets_id="euets",
        )
        .rename(columns=col_rename)
        .rename(columns=lambda x: x.lower())
    )
    # assign account and installation ids
    for prefix in ["acquiring", "transferring"]:
        # account identifier
        mask = df_trans[f"{prefix}_account_identifier"].notna()
        df_trans.loc[mask, f"{prefix}_account_id"] = (
            df_trans.loc[mask, f"{prefix}_registry_id"]
            + "_"
            + df_trans.loc[mask, f"{prefix}_account_identifier"].astype(int).astype(str)
        )
        # installation identifier
        mask = df_trans[f"{prefix}_installation_installation_identifier"].notna()
        df_trans.loc[mask, f"{prefix}_installation_id"] = (
            df_trans.loc[mask, f"{prefix}_registry_id"]
            + "_"
            + df_trans.loc[mask, f"{prefix}_installation_installation_identifier"]
            .astype(int)
            .astype(str)
        )
    if fn_out is not None:
        df_trans.to_csv(fn_out, index=False)
    return df_trans


def normalize_accounts(
    df: pd.DataFrame, fn_out: str | Path | None = None
) -> pd.DataFrame:
    """Normalize account data from the given DataFrame.

    Deprecated: Account data are treated separately in the account holder extraction
        that also handles normalization. Be aware that the data created by this
        function are not part of the standard pipeline.

    Args:
        df (pd.DataFrame): DataFrame containing raw account data.
        fn_out (str | Path | None): Optional output filename to save the normalized
            data.

    Returns:
        pd.DataFrame: DataFrame containing normalized account data.
    """
    warnings.warn(
        (
            "Account data are treated separately in the account holder extraction that"
            " also handles normalization. Be aware that the data created by this "
            "function are not part of the standard pipeline."
        ),
        DeprecationWarning,
        stacklevel=2,
    )
    # some column renaming (mainly to lower case)
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }

    # do minor transformations including creating a unique account id
    df_acc = (
        df.assign(
            account_id=lambda df: (
                df.REGISTRY_CODE + "_" + df.ACCOUNT_IDENTIFIER.astype(str)
            ),
            # TODO some missings here which seem to be national ETS2 accounts
            account_type_id=lambda df: df.FULL_TYPE.fillna(df.ETS_ACCOUNT_TYPE).map(
                map_account_type_inv
            ),
            closure_pending=lambda df: df.IS_CLOSURE_PENDING == "Y",
        )
        .drop(columns=["ACCOUNT_IDENTIFIER", "IS_CLOSURE_PENDING"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
        .assign(ets_id="euets")
    )
    if fn_out is not None:
        df_acc.to_csv(fn_out, index=False)
    return df_acc


def normalize_all_data(dir_in: Path, dir_out: Path) -> None:
    """Normalize all datasets in the given input directory and save the normalized
    data to the given output directory.

    Args:
        dir_in (Path): Directory containing the raw data files.
        dir_out (Path): Directory to save the normalized data files.
    """
    # accounts
    # Note: accounts are fully handled in the account holder extraction and are
    # not part of the standard pipeline.
    # df_accounts = pd.read_csv(dir_in / "eutl_accounts.csv", low_memory=False)
    # df_accounts_norm = normalize_accounts(df_accounts)
    # df_accounts_norm.to_csv(dir_out / "eutl_accounts.csv", index=False)

    # compliance
    df_compliance = pd.read_csv(dir_in / "eutl_compliance.csv", low_memory=False)
    df_compliance_norm = normalize_compliance(df_compliance)
    df_compliance_norm.to_csv(dir_out / "eutl_compliance.csv", index=False)

    # installations
    df_installations = pd.read_csv(dir_in / "eutl_installations.csv", low_memory=False)
    df_installations_norm = normalize_installations(df_installations)
    df_installations_norm.to_csv(dir_out / "eutl_installations.csv", index=False)

    # transactions
    df_transactions = pd.read_csv(dir_in / "eutl_transactions.csv", low_memory=False)
    df_transactions_norm = normalize_transactions(df_transactions)
    df_transactions_norm.to_csv(dir_out / "eutl_transactions.csv", index=False)
