"""Module for normalizing data. Normalization includes minor transformations
and standardizing column names. The main transformations are:

- Creating unique IDs for accounts and installations by combining registry codes
  with their respective identifiers.
- Renaming columns to lower case for consistency.
- Assigning a constant ETS ID to stamp the system where the data come from
- basic cleaning and type conversions."""

import pandas as pd

from eutl_scraper.mappings import map_account_type_inv

from .mappings import map_registryCode_inv


def compliance(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize compliance data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw compliance data.

    Returns:
        pd.DataFrame: DataFrame containing normalized compliance data.
    """
    # do minor transformations including creating a unique installation ID
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }
    df_c = (
        df.assign(
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
    return df_c


def installations(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize installation data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw installation data.

    Returns:
        pd.DataFrame: DataFrame containing normalized installation data.
    """
    # do minor transformations including creating a unique installation ID
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }
    df_inst = (
        df.assign(
            installation_id=(
                lambda df: df.REGISTRY_CODE
                + "_"
                + df.INSTALLATION_IDENTIFIER.astype(str)
            ),
            account_id=(
                lambda df: df.ACCOUNT_REGISTRY_CODE
                + "_"
                + df.ACCOUNT_IDENTIFIER.astype(str)
            ),
            ets_id="euets",
            snapshot_date=pd.to_datetime(df.SNAPSHOT_DATE, format="%Y-%m-%d"),
        )
        .drop(columns=["INSTALLATION_IDENTIFIER"])
        .rename(columns=map_col)
        .rename(columns=lambda x: x.lower())
    )
    return df_inst


def transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize transaction data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw transaction data.

    Returns:
        pd.DataFrame: DataFrame containing normalized transaction data.
    """
    df_trans = df.assign(
        # add the registry ids
        acquiring_registry_id=(
            lambda df: df.ACQUIRING_REGISTRY_NAME.map(map_registryCode_inv)
        ),
        transferring_registry_id=(
            lambda df: df.TRANSFERRING_REGISTRY_NAME.map(map_registryCode_inv)
        ),
        originating_registry_id=(
            lambda df: df.ORIGINATING_REGISTRY.map(map_registryCode_inv)
        ),
        ets_id="euets",
    ).rename(columns=lambda x: x.lower())
    # assign account and installation ids
    for prefix in ["acquiring", "transferring"]:
        # account identifier
        df_trans[f"{prefix}_account_id"] = (
            df_trans[f"{prefix}_registry_id"]
            + "_"
            + df_trans[f"{prefix}_account_identifier"].astype(str)
        )
        # installation identifier
        mask = df_trans[f"{prefix}_installation_installation_identifier"].notna()
        df_trans.loc[mask, f"{prefix}_installation_id"] = (
            df_trans.loc[mask, f"{prefix}_registry_id"]
            + "_"
            + df_trans.loc[
                mask, f"{prefix}_installation_installation_identifier"
            ].astype(str)
        )
    return df_trans


def accounts(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize account data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing raw account data.

    Returns:
        pd.DataFrame: DataFrame containing normalized account data.
    """
    # some column renaming (mainly to lower case)
    map_col = {
        "REGISTRY_CODE": "registry_id",
    }

    # do minor transformations including creating a unique account id
    df_acc = (
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
        .assign(ets_id="euets")
    )
    return df_acc
