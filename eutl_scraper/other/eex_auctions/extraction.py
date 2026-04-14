"""Module for extracting price data from Excel and ZIP files downloaded from the
EEX website."""

import warnings
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


def detect_header_row(df: pd.DataFrame) -> int | None:
    """Determine the header row in a DataFrame by looking for a row that
    contains "date" (case-insensitive).

    Args:
        df: A DataFrame to search for the header row.

    Returns:
        The index of the header row, or None if no header row is found.
    """
    for i, row in df.iterrows():
        if row.astype(str).str.lower().str.contains("date", na=False).any():
            return i
    return None


def extract_raw_data(df: pd.DataFrame, max_rows: int) -> pd.DataFrame | None:
    """Extract the Date and Auction Price columns from the given Excel file.

    Args:
        df: The DataFrame to extract data from.
        max_rows: The maximum number of rows to search for the header row.

    Returns:
        A DataFrame with the raw data extracted from the Excel file
    """
    # find the header row by looking for a row that contains "date" (case-insensitive)
    idx_header_row = None
    for i, row in df.iterrows():
        if row.astype(str).str.lower().str.contains("date", na=False).any():
            idx_header_row = i
            break
        if i >= max_rows:
            break
    if idx_header_row is None:
        return None

    # extract the data starting from the header row
    columns = df.iloc[idx_header_row].astype(str).str.strip().str.replace("\n", " ")
    # ensure consistent column names for the price column
    columns = columns.str.replace("Auction Price EUR/tCO2", "Auction Price €/tCO2")

    # exclude unnamed columns
    mask = ~columns.isin(["nan", "", pd.NA])
    result = df.iloc[idx_header_row + 1 :, mask.values].reset_index(drop=True)
    result.columns = columns[mask]
    return result


def extract_data_from_excel(file_path: str | Path | BytesIO) -> pd.DataFrame:
    """Extract the Date and Auction Price columns from the given Excel file.

    Args:
        file_path (str | Path | BytesIO): The path to the Excel file to extract
            data from.

    Returns:
        A DataFrame with the extracted data.
    """
    sheet_name = "Primary Market Auction"
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Workbook contains no default style")
        df = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
        )
    df = extract_raw_data(df, max_rows=120)

    if df.empty:
        raise ValueError(f"No valid data found in Excel file {file_path}")

    return df


def extract_data_from_zip(zip_path: str | Path) -> pd.DataFrame:
    """Extract data from Excel files contained in a ZIP archive.

    Args:
        zip_path (str | Path): The path to the ZIP file to extract data from.

    Returns:
        A DataFrame with the extracted data from all Excel files in the ZIP.

    Raises:
        ValueError: If no valid data is found in any of the Excel files in the ZIP
    """
    lst_df = []
    with ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith((".xlsx", ".xls")):
                continue
            with zf.open(name) as f:
                df = extract_data_from_excel(BytesIO(f.read()))
                if df is not None and not df.empty:
                    lst_df.append(df)

    if not lst_df:
        raise ValueError(f"No valid data found in {zip_path}")

    return pd.concat(lst_df, ignore_index=True)


def extract_data(file_path: str | Path) -> pd.DataFrame:
    """Extract price data from an Excel or ZIP file.

    Args:
        file_path (str | Path): The path to the file to extract data from. Can be
            an Excel file (.xlsx or .xls) or a ZIP file containing Excel files.
    Returns:
        A DataFrame with the extracted price data.

    Raises:
        ValueError: If the file type is unsupported or if no valid data is found.
    """
    file_path = Path(file_path)

    if file_path.suffix.lower() == ".zip":
        return extract_data_from_zip(file_path)
    if file_path.suffix.lower() in (".xlsx", ".xls"):
        return extract_data_from_excel(file_path)

    raise ValueError(f"Unsupported file type: {file_path.suffix}")
