"""Functions to assign NACE codes to installations
Nace codes are assigned based on the leakage lists, that assigned NACE codes
to installations in 2015 and 2020.
"""

from pathlib import Path

import pandas as pd

from ..settings import DIR_EXTRACTED
from .nace_from_leakage_lists import extract_nace_by_installation, extract_nace_scheme

MY_DIR = Path(__file__).resolve().parent


def pipeline_nace_from_leakage_lists(
    dir_out: str | Path | None = None,
    fn_leakage_2015: str | Path | None = None,
    fn_leakage_2020: str | Path | None = None,
    fn_nace_scheme: str | Path | None = None,
) -> pd.DataFrame:
    """Pipeline to extract NACE codes from leakage lists and save to disk

    Args:
        dir_out (str | Path | None): output directory to save the data
            If none is provided, the default directory will be used
        fn_out (str | Path): output file name
            If none is provided, the default file will be used
            (./data/extracted/nace_from_leakage_lists.csv).
        fn_leakage_2015 (str | Path | None): path to 2015 leakage list
            If none is provided, the default file will be used
        fn_leakage_2020 (str | Path | None): path to 2020 leakage list
            If none is provided, the default file will be used
        fn_nace_scheme (str | Path | None): path to NACE scheme file
            If none is provided, the default file will be used

    Returns:
        pd.DataFrame: with nace classification by installation
    """
    # set default paths if not provided
    if dir_out is None:
        dir_out = DIR_EXTRACTED
    if fn_leakage_2015 is None:
        fn_leakage_2015 = MY_DIR / "leakage_2015.xlsx"
    if fn_leakage_2020 is None:
        fn_leakage_2020 = MY_DIR / "leakage_2020.xlsx"
    if fn_nace_scheme is None:
        fn_nace_scheme = MY_DIR / "NACE_REV2_20200427_154248.htm"
    dir_out = Path(dir_out)
    fn_leakage_2015 = Path(fn_leakage_2015)
    fn_leakage_2020 = Path(fn_leakage_2020)
    fn_nace_scheme = Path(fn_nace_scheme)

    df_nace = extract_nace_scheme(fn_in=fn_nace_scheme)
    df_nace_by_installation = extract_nace_by_installation(
        fn_leakage_2015=fn_leakage_2015,
        fn_leakage_2020=fn_leakage_2020,
        df_nace_codes=df_nace,
    )

    # save to disk
    fn_out = dir_out / "nace_from_leakage_lists.csv"
    df_nace_by_installation.to_csv(fn_out, index=False)
    fn_out = dir_out / "nace_scheme.csv"
    df_nace.to_csv(fn_out, index=False)

    return df_nace_by_installation
