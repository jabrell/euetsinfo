from pathlib import Path

import pandas as pd
from loguru import logger

from eutl_scraper.settings import Settings

from .nace_from_leakage_lists import extract_nace_by_installation, extract_nace_scheme

MY_DIR = Path(__file__).resolve().parent


def pipeline_nace_from_leakage_lists(
    settings: Settings,
    save_to_disk: bool = True,
    fn_leakage_2015: str | Path | None = None,
    fn_leakage_2020: str | Path | None = None,
    fn_nace_scheme: str | Path | None = None,
    drop_missing_installations: bool = True,
) -> pd.DataFrame:
    """Pipeline to extract NACE codes from leakage lists and save to disk

    Args:
        settings (Settings): Settings object containing configuration.
        save_to_disk (bool): Whether to save the extracted data to disk.
            Defaults to True.
        fn_leakage_2015 (str | Path | None): path to 2015 leakage list
            If none is provided, the default file will be used
        fn_leakage_2020 (str | Path | None): path to 2020 leakage list
            If none is provided, the default file will be used
        fn_nace_scheme (str | Path | None): path to NACE scheme file
            If none is provided, the default file will be used
        drop_missing_installations (bool): Whether to drop installations that have
            a NACE code but the installation is not known from the EUTL data.
            Defaults to True.

    Returns:
        pd.DataFrame: with nace classification by installation
    """
    # set default paths if not provided
    if fn_leakage_2015 is None:
        fn_leakage_2015 = MY_DIR / "leakage_2015.xlsx"
    if fn_leakage_2020 is None:
        fn_leakage_2020 = MY_DIR / "leakage_2020.xlsx"
    if fn_nace_scheme is None:
        fn_nace_scheme = MY_DIR / "NACE_REV2_20200427_154248.htm"
    fn_leakage_2015 = Path(fn_leakage_2015)
    fn_leakage_2020 = Path(fn_leakage_2020)
    fn_nace_scheme = Path(fn_nace_scheme)

    logger.info("Starting NACE codes extraction pipeline...", filter="nace_pipeline")
    df_nace = extract_nace_scheme(fn_in=fn_nace_scheme)
    df_nace_by_installation = extract_nace_by_installation(
        fn_leakage_2015=fn_leakage_2015,
        fn_leakage_2020=fn_leakage_2020,
        df_nace_codes=df_nace,
    )

    # drop installations that are not in the eutl data
    if drop_missing_installations:
        df_eutl = pd.read_csv(settings.fp("installations", settings.dir_extracted))
        known_installations = set(df_eutl.installation_id)
        no_installation = (
            set(df_nace_by_installation.installation_id) - known_installations
        )
        if len(no_installation) > 0:
            msg = f"Dropping {len(no_installation)} installations not found in EUTL."
            logger.warning(msg, filter="nace_pipeline")
            df_nace_by_installation = df_nace_by_installation[
                ~df_nace_by_installation.installation_id.isin(no_installation)
            ]

    # save to disk
    if save_to_disk:
        logger.info("Saving extracted NACE data to disk...", filter="nace_pipeline")
        fn_out = settings.fp("nace_from_leakage_lists", settings.dir_extracted)
        df_nace_by_installation.to_csv(fn_out, index=False)
        fn_out = settings.fp("nace_scheme", settings.dir_extracted)
        df_nace.to_csv(fn_out, index=False)

    return df_nace_by_installation
