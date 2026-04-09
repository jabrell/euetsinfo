from pathlib import Path

import pandas as pd

from ..mappings import map_registryCode_inv
from .utils import _strip_str


def _clean_and_create_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Clean transaction data and create unique account and installation IDs.

    Args:
        df (pd.DataFrame): DataFrame containing raw transaction data.

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
    return df_trans


def _rename_and_check_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Extract transaction data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the transactions data after
            normalization.

    Returns:
        pd.DataFrame: DataFrame containing transaction data.
    """
    # transaction data
    transaction_columns = [
        "transaction_id",
        "transaction_type",
        "transaction_date",
        # "transaction_status",  # drop status as we anyways only observe 'completed'
        "ets_id",
        "originating_registry_id",
        "acquiring_registry_id",
        "acquiring_account_id",
        "acquiring_installation_id",
        "transferring_registry_id",
        "transferring_account_id",
        "transferring_installation_id",
        "unit_type_description",
        "supp_unit_type_description",
        "amount",
    ]
    df_trans = df[transaction_columns].assign(
        transaction_date=lambda df: pd.to_datetime(df.transaction_date)
    )
    return df_trans


def _create_projects(df: pd.DataFrame) -> pd.DataFrame:
    """Extract unique projects from the transaction DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing transaction data.

    Returns:
        pd.DataFrame: DataFrame containing unique project data.
    """

    def impose_project_type(unit_type_desc: str) -> str | None:
        if "RMU" in unit_type_desc:
            return "RMU"
        if "CER" in unit_type_desc:
            return "CER"
        if "tCER" in unit_type_desc:
            return "tCER"
        if "ERU" in unit_type_desc:
            return "ERU"
        return

    project_columns = [
        "originating_registry_id",
        "amount",
        "project_identifier",
        "lulucf_code_description",
        "unit_type_description",
        "track",
        "expiry_date",
    ]
    df_projects = (
        df[project_columns]
        .dropna(subset=["project_identifier"])
        .drop_duplicates(subset=["project_identifier"])
        .assign(
            project_type=lambda df: df.unit_type_description.map(impose_project_type),
            project_id=lambda df: df.project_identifier.astype("int"),
            expiry_date=lambda df: pd.to_datetime(df.expiry_date),
        )
        .drop(columns=["unit_type_description"])
    )
    return df_projects


def extract_transactions(
    fn_source: Path, fn_out: str | Path | None = None
) -> pd.DataFrame:
    """Extract transaction data

    Args:
        fn_source (Path): Path to the source file containing raw transaction data.
        fn_out (str | Path | None): Optional output filename to save the data.

    Returns:
        pd.DataFrame: DataFrame containing transaction data.
    """
    df = (
        pd.read_csv(fn_source, low_memory=False)
        .pipe(_clean_and_create_ids)
        .pipe(_rename_and_check_transactions)
    )

    if fn_out is not None:
        df.to_csv(fn_out, index=False)

    return df


def extract_projects(fn_source: Path, fn_out: str | Path | None = None) -> pd.DataFrame:
    """Extract unique project data from the transaction DataFrame.

    Args:
        fn_source (Path): Path to the source file containing raw transaction data.
        fn_out (str | Path | None): Optional output filename to save the data.

    Returns:
        pd.DataFrame: DataFrame containing unique project data.
    """
    df = (
        pd.read_csv(fn_source, low_memory=False)
        .pipe(_clean_and_create_ids)
        .pipe(_create_projects)
    )

    if fn_out is not None:
        df.to_csv(fn_out, index=False)
    return df
