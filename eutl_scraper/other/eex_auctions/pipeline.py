import pandas as pd
from loguru import logger

from eutl_scraper.settings import Settings

from .download import download_auction_reports
from .extraction import extract_data
from .parsing import parse_auctions


def pipeline_eex_auctions(
    settings: Settings,
    download_history: bool = False,
    save_extracted: bool = True,
) -> pd.DataFrame | None:
    """Download EUA Primary Auction from the EEX website and extract the data
    into a DataFrame.

    Args:
        settings (Settings): The settings object containing configuration values.
        download_history (bool): Whether to also download the historical data ZIP file.
        save_extracted (bool): Whether to save the extracted data as a CSV file in
            the extracted data directory.
            Defaults to True.

    Returns:
        A DataFrame with the extracted auction price data, or None if no data was
        extracted.

    Raises:
        ValueError: If no valid data is extracted from the downloaded files.
    """
    logger.info("Starting EEX auctions pipeline...", filter="eex_auctions_pipeline")
    fn_xls, fn_zip = download_auction_reports(
        settings=settings, download_history=download_history
    )
    logger.info(
        "Download completed. Extracting data...", filter="eex_auctions_pipeline"
    )
    df = extract_data(fn_xls) if fn_xls else None
    if download_history and fn_zip:
        df_zip = extract_data(fn_zip)
        df = pd.concat([df, df_zip], ignore_index=True) if df is not None else df_zip
    if df is None or df.empty:
        raise ValueError("No valid data extracted from the downloaded files")
    df = parse_auctions(df) if df is not None else None

    # add a timestamp column with the current date and time
    if df is not None:
        df["created_at"] = pd.Timestamp.now()

    if save_extracted and df is not None:
        fn_out = settings.fp("eex_auctions", settings.dir_extracted)
        df.to_csv(fn_out, index=False)
    return df
