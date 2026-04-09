from pathlib import Path

import pandas as pd

from .utils import _strip_str


def _clean_and_create_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw installation data and create unique installation and account IDs.

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
    return df_inst


def _rename_and_check(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns and check for unique and non-missing installation IDs.

    Args:
        df (pd.DataFrame): DataFrame containing the installations data after
            the normalization step.

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
    return df_installation


def extract_installations(
    fn_source: Path, fn_out: str | Path | None = None
) -> pd.DataFrame:
    """Extract installation data from the given source file and save to output file.

    Args:
        fn_source (Path): Path to the source CSV file containing raw installation data.
        fn_out (str | Path | None): Optional output filename to save the extracted
            data. If None, the extracted data will not be saved to a file.

    Returns:
        pd.DataFrame: DataFrame containing extracted installation data.
    """
    df = pd.read_csv(fn_source).pipe(_clean_and_create_ids).pipe(_rename_and_check)
    if fn_out is not None:
        df.to_csv(fn_out, index=False)
    return df
