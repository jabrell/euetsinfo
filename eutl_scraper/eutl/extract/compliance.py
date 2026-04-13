import pandas as pd
from loguru import logger

from eutl_scraper.settings import Settings

from .utils import _strip_str


def _clean_and_create_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the raw compliance data and create unique installation IDs.

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
    return df_c


def _rename_and_check(df: pd.DataFrame) -> pd.DataFrame:
    """Extract compliance data from the given DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing the compliance data after normalization.

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
    return df_comp


def extract_compliance(settings: Settings, save_to_disk: bool = True) -> pd.DataFrame:
    """Extract compliance data from the given source file.

    Args:
        settings (Settings): Settings object containing configuration.
        save_to_disk (bool): Whether to save the extracted data to disk.
            Defaults to True.

    Returns:
        pd.DataFrame: DataFrame containing extracted compliance data.
    """
    logger.info("Extracting compliance data...", filter="eutl_extract")
    df = (
        pd.read_csv(settings.fp("compliance", settings.dir_source))
        .pipe(_clean_and_create_ids)
        .pipe(_rename_and_check)
    )
    if save_to_disk:
        logger.info(
            "Saving extracted compliance data to disk...", filter="eutl_extract"
        )
        df.to_csv(settings.fp("compliance", settings.dir_extracted), index=False)
    return df
