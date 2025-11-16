"""The module for extracting the basic tables from the EUTL data downloads."""

import pandas as pd


def installations(df: pd.DataFrame, fn_out: str | None = None) -> pd.DataFrame:
    """Extract installation data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the installations data after
            the normalization step.
        fn_out (str | None, optional): Output filename to save the data.
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


def compliance(df: pd.DataFrame, fn_out: str | None = None) -> pd.DataFrame:
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
