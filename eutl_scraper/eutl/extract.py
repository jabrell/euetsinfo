"""The module for extracting the basic tables from the EUTL data downloads."""

import logging
from pathlib import Path

import pandas as pd

from .extract_accounts import create_account_table_with_holders


def extract_installations(df: pd.DataFrame, fn_out: Path | None = None) -> pd.DataFrame:
    """Extract installation data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the installations data after
            the normalization step.
        fn_out (Path | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing installation data.

    Raises:
        ValueError: If installation IDs are not unique or if any installation ID
            is missing.
    """
    # Filter and return installation-related columns
    installation_cols = [
        "installation_id",
        "ets_id",
        "account_id",
        "registry_id",
        "registry_name",
        "installation_name",
        "eper_identification",
        "activity_type_code",
        "activity_type",
        "permit_identifier",
        "permit_revocation_date",
        "city",
        "postal_code",
        "address1",
        "address2",
        "year_of_first_emissions",
        "year_of_last_emissions",
        "snapshot_date",
    ]
    # ensure that we do not have duplicated or missing installation IDs
    if not df.installation_id.is_unique:
        raise ValueError("Installation IDs are not unique.")
    if df.installation_id.isnull().any():
        raise ValueError("Some installation IDs are missing.")
    df_installation = df[installation_cols].copy()
    if fn_out is not None:
        df_installation.to_csv(fn_out, index=False)
    return df_installation


def extract_compliance(df: pd.DataFrame, fn_out: Path | None = None) -> pd.DataFrame:
    """Extract compliance data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the compliance data after normalization.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing compliance data.

    Raises:
        ValueError: If the compliance data is not unique by installation ID and year.
    """
    # TODO Should we factor out surrendering details into a separate table?
    col_map = {
        "installation_id": "installation_id",
        "installation_name": "installation_name",
        "registry_id": "registry_id",
        "registry_name": "registry_name",
        "year": "year",
        # allocations
        "allocation": "allocated",
        "ch_allocation": "allocated_ch",
        "allocation_res": "allocation_res",
        "allocation_tra": "allocation_tra",
        # verified emissions
        "verified_emissions": "verified",
        "ch_verified_emissions": "verified_ch",
        # surrendering
        "surr_all": "surrendered",
        "surr_eua": "surrendered_eua",
        "surr_euaa": "surrendered_euaa",
        "surr_chu": "surrendered_chu",
        "surr_chua": "surrendered_chua",
        "surr_eru_from_aau": "surrendered_eru_from_aau",
        "surr_former_eua": "surrendered_former_eua",
        "surr_cer": "surrendered_cer",
        # excluded flags
        "excluded": "excluded",
        "ch_excluded": "ch_excluded",
        # snapshot date
        "snapshot_date": "snapshot_date",
    }

    # check that the data by year and installation ID is unique
    if not df.set_index(["installation_id", "year"]).index.is_unique:
        raise ValueError("Compliance data is not unique by installation ID and year.")

    df_comp = df.rename(columns=col_map)[list(col_map.values())].copy()
    if fn_out is not None:
        df_comp.to_csv(fn_out, index=False)
    return df_comp


def extract_transactions(
    df: pd.DataFrame, dir_out: Path | None
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Extract transaction data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the transactions data after
            normalization.
        dir_out (Path | None): Output directory to save the data. As we extract
            several tables here, we need the directory instead of a single filename.
                The files will be named
                - 'transactions.csv': Contains the transaction data
                    (without details on the parties).
                - 'projects.csv': Contains data on the projects involved in
                    transactions.
                - 'transaction_parties.csv': Contains data on the parties involved in
                    transactions.
            If none, the extracted dataframes will not be saved to disk.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: DataFrames containing
            transaction data, project data, and account data.
    """
    # separate out the project and account data from the transactions
    df_projects = extract_projects_from_transactions(df)
    df_accounts = extract_accounts_from_transactions(df)

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
    # save the dataframes
    if dir_out is not None:
        dir_out = Path(dir_out)
        df_trans.to_csv(dir_out / "eutl_transactions.csv", index=False)
        df_projects.to_csv(dir_out / "eutl_projects.csv", index=False)
        df_accounts.to_csv(dir_out / "eutl_transaction_parties.csv", index=False)
    return df_trans, df_projects, df_accounts


def extract_projects_from_transactions(
    df: pd.DataFrame, fn_out: str | None = None
) -> pd.DataFrame:
    """Extract unique projects from the transaction DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing transaction data.
        fn_out (str | None, optional): Output filename to save the data.
            Defaults to None.

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
    if fn_out is not None:
        df_projects.to_csv(fn_out, index=False)
    return df_projects


def extract_accounts_from_transactions(
    df: pd.DataFrame, fn_out: Path | None = None
) -> pd.DataFrame:
    """Extract account information from transactions DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing transaction data.
        fn_out (Path | None, optional): Output filename to save the data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing unique account information.
    """
    cols_accounts = [
        "account_id",
        "installation_id",
        "registry_id",
        "registry_name",
        "account_type1",
        "account_type2",
        "account_type3",
        "account_open_dt",
        "account_end_of_validity",
        "account_name",
        "account_identifier",
        "account_holder",
        "account_holder_address1",
        "account_holder_address2",
        "account_holder_city",
        "account_holder_postal_code",
        "account_holder_country_code",
        "account_holder_company_registration_number",
        "account_holder_lei",
        "installation_name",
        "installation_installation_identifier",
        "installation_permit_identifier",
        "installation_parent_company",
        "installation_subsidiary_company",
        "installation_eper_identification",
        "installation_city",
        "installation_postal_code",
        "installation_address1",
        "installation_address2",
        "installation_main_activity",
    ]

    lst_df = []
    for prefix in ["acquiring", "transferring"]:
        _cols = {f"{prefix}_{col}": col for col in cols_accounts}
        df_ = df[list(_cols.keys())].rename(columns=_cols).drop_duplicates()
        lst_df.append(df_)
    df_accounts = pd.concat(lst_df).drop_duplicates()
    if fn_out is not None:
        df_accounts.to_csv(fn_out, index=False)
    return df_accounts


def create_missing_installations(
    fn_compliance: Path, fn_installations: Path
) -> pd.DataFrame:
    """Create a DataFrame containing the missing installations based on the
    compliance data. These are accounts related to ETS2 installations that are
    present in the compliance data but not in the installation data.

    Note: That modifies the installation table by adding the missing installations.


    Args:
        fn_compliance (Path): Path to the CSV file containing the compliance data.
        fn_installations (Path): Path to the CSV file containing the installation data.

    Returns:
        pd.DataFrame: DataFrame containing the missing installations.
    """
    df_compliance = pd.read_csv(fn_compliance, low_memory=False)
    df_installations = pd.read_csv(fn_installations, low_memory=False)
    missing_ids = set(df_compliance["installation_id"]) - set(
        df_installations["installation_id"]
    )
    logging.info(
        f"{len(missing_ids)} missing installation IDs found in compliance data."
        " Added to installation data under ETS2 system."
    )
    df_missing = (
        df_compliance[df_compliance["installation_id"].isin(missing_ids)]
        .drop_duplicates(subset=["installation_id"])[
            ["installation_id", "installation_name", "registry_id", "registry_name"]
        ]
        .assign(ets_id="ets2")
    )

    # add the missing installations to the installation table
    df_inst_new = pd.concat([df_installations, df_missing], ignore_index=True)
    df_inst_new.to_csv(fn_installations, index=False)
    return df_missing


def extract_all_data(
    dir_in: Path, dir_out: Path, fn_manual_accounts: Path, dir_source: Path
) -> None:
    """Extract all tables from the normalized EUTL data.

    Args:
        dir_in (Path): Directory containing the normalized EUTL data.
        dir_out (Path): Directory to save the extracted tables.
        fn_manual_accounts (Path): Filename of the manually downloaded account data.
            This is required for the account holder extraction step. If not provided,
            an error will be raised in that step. Note that the account holder
            extraction step also requires the extracted transactions to be present
            in the extracted directory.
        dir_source (Path ): Directory containing the source data.
    """
    dir_in = Path(dir_in)
    dir_out = Path(dir_out)
    dir_source = Path(dir_source)
    df_installations = pd.read_csv(dir_in / "eutl_installations.csv", low_memory=False)
    extract_installations(df_installations, fn_out=dir_out / "eutl_installations.csv")

    df_compliance = pd.read_csv(dir_in / "eutl_compliance.csv", low_memory=False)
    extract_compliance(df_compliance, fn_out=dir_out / "eutl_compliance.csv")

    df_transactions = pd.read_csv(dir_in / "eutl_transactions.csv", low_memory=False)
    extract_transactions(df_transactions, dir_out=dir_out)

    # extract accounts together with the account holders based on the transactions
    # and the manually downloaded account data
    fn_direct = dir_source / "eutl_accounts.csv"
    fn_trans = dir_source / "eutl_transactions.csv"
    create_account_table_with_holders(
        fn_direct=fn_direct,
        fn_bi=fn_manual_accounts,
        fn_trans=fn_trans,
        dir_out=dir_out,
    )

    create_missing_installations(
        fn_compliance=dir_out / "eutl_compliance.csv",
        fn_installations=dir_out / "eutl_installations.csv",
    )
