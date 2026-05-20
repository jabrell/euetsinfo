"""This module provides functions to assign NACE classifications to installations.
It includes functions to parse leakage lists from 2015 and 2020, merge them, and
extract NACE classification schemes from HTML files.
"""

from pathlib import Path

import pandas as pd

# Directory containing manual source data files relative to this module
MY_DIR = Path(__file__).resolve().parent


def extract_nace_by_installation(
    fn_leakage_2015: Path,
    fn_leakage_2020: Path,
    df_nace_codes: pd.DataFrame,
) -> pd.DataFrame:
    """Parse leakage lists and extract NACE classifications

    Args:
        fn_leakage_2015 (Path): path to 2015 leakage list
        fn_leakage_2020 (Path): path to 2020 leakage list
        df_nace_codes (pd.DataFrame): DataFrame containing NACE classification
            scheme

    Returns:
        pd.DataFrame: with nace classification by installation
            columns: installation_id, nace_2015, nace_2020
    """
    # set path to input files
    if fn_leakage_2015 is None:
        fn_leakage_2015 = MY_DIR / "leakage_2015.xlsx"
    if fn_leakage_2020 is None:
        fn_leakage_2020 = MY_DIR / "leakage_2020.xlsx"
    fn_leakage_2015 = Path(fn_leakage_2015)
    fn_leakage_2020 = Path(fn_leakage_2020)

    df_15 = extract_leakage_2015(fn_leakage_2015=fn_leakage_2015)
    df_20 = extract_leakage_2020(fn_leakage_2020=fn_leakage_2020)

    # merge the two leakage lists and normalize NACE codes
    df = df_15.merge(df_20, on="installation_id", how="outer")

    # normalized NACE codes
    df = normalize_nace_codes(
        df=df, columns=["nace_2015", "nace_2020"], df_nace_codes=df_nace_codes
    ).assign(created_at=pd.Timestamp.now())
    return df


def normalize_nace_codes(
    df: pd.DataFrame, columns: str | list[str], df_nace_codes: pd.DataFrame
) -> pd.DataFrame:
    """Some codes are formatted as 4-digit but are a lower level NACE code
    e.g., 35.00 is 2-digit 35 and 35.10 is 3-digit 35.1. This function normalizes
    the NACE codes in the provided dataframe.

    Args:
        df (pd.DataFrame): DataFrame containing NACE codes
        columns (str | list[str]): Column name(s) containing NACE codes to normalize

    Returns:
        pd.DataFrame: DataFrame with normalized NACE codes
    """
    if isinstance(columns, str):
        columns = [columns]

    valid_ids = set(df_nace_codes["id"].astype(str).tolist())
    for column in columns:
        df[column] = df[column].where(
            df[column].isin(valid_ids),
            df[column].str.rstrip(".0"),
        )
    return df


def extract_leakage_2015(
    fn_leakage_2015: str | Path, fn_out: str | None = None
) -> pd.DataFrame:
    """Parse 2015 leakage list

    Args:
        fn_leakage_2015 (str): path to 2015 leakage list
        fn_out (str | None): output file name
            If none is provided, the data frame is not saved to disk.
            Default is None.

    Returns:
        pd.DataFrame: with nace classification by installation
            columns: installation_id, nace15
    """
    df = (
        pd.read_excel(fn_leakage_2015, na_values="-", dtype={"NACE Rev2": str})
        .assign(
            installation_id=lambda df_: (
                df_["COUNTRY_CODE"] + "_" + df_["INSTALLATION_IDENTIFIER"].astype("str")
            ),
            nace_2015=lambda df_: df_["NACE Rev2"],
        )[["installation_id", "nace_2015"]]
        .loc[lambda df_: df_["nace_2015"].notnull()]
    )

    if fn_out:
        df.to_csv(fn_out, index=False)
    return df


def extract_leakage_2020(
    fn_leakage_2020: str | Path, fn_out: str | None = None
) -> pd.DataFrame:
    """Parse 2020 leakage list

    Args:
        fn_leakage_2020 (str): path to 2020 leakage list
        fn_out (str | None): output file name
            If none is provided, the data frame is not saved to disk.
            Default is None.

    Returns:
        pd.DataFrame: with nace classification by installation
            columns: installation_id, nace15
    """
    df = (
        pd.read_excel(fn_leakage_2020, skiprows=2, dtype={"NACE Rev2": str})
        .assign(
            installation_id=lambda df_: (
                df_["COUNTRY_CODE"] + "_" + df_["INSTALLATION_IDENTIFIER"].astype("str")
            ),
            nace_2020=lambda df_: df_["NACE Rev2"],
        )[["installation_id", "nace_2020"]]
        .loc[lambda df_: df_["nace_2020"].notnull()]
    )

    if fn_out:
        df.to_csv(fn_out, index=False)
    return df


def extract_nace_scheme(fn_in: str | Path) -> pd.DataFrame:
    """Extract NACE codes with sub-classification from html
    file provided by Eurostat RAMON

    Args:
        fn_in (str | Path): input html file path

    Returns:
        pd.DataFrame: with NACE classification scheme
    """
    df_in = pd.read_html(fn_in)[0]

    # bring all levels into one dataframe and structure them
    col_rename = {
        "Code": "id",
        "Level": "level",
        "Parent": "parent_id",
        "Description": "description",
        "This item includes": "includes",
        "This item also includes": "includesAlso",
        "Rulings": "ruling",
        "This item excludes": "excludes",
        "Reference to ISIC Rev. 4": "isic4_id",
    }
    df_all = df_in.rename(columns=col_rename)[col_rename.values()].copy()

    # Need to add the level 3 codes ending with .0 as they are sometime used
    new_rows = []
    for i, row in df_all[df_all.level == 2].iterrows():
        if row["id"] + ".0" not in df_all.id.values:
            r = {k: v for k, v in row.items()}
            r["id"] = r["id"] + ".0"
            r["level"] = 3
            r["parent_id"] = row["id"]
            r["isic4_id"] = r["isic4_id"] + "0"
            new_rows.append(r)
    df_ = pd.DataFrame(new_rows)

    # return combined dataframe with all levels
    df_out = pd.concat([df_all, df_]).assign(created_at=pd.Timestamp.now())
    return df_out
