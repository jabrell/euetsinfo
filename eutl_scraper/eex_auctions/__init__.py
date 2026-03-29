from pathlib import Path

import pandas as pd

from eutl_scraper import settings

from .download import download_auction_reports
from .eex_fetch import update_eex_auction_prices
from .extraction import extract_data
from .parsing import parse_auctions

__all__ = ["update_eex_auction_prices", "download_auction_data"]


def download_auction_data(
    fn_out: str | Path | None,
    download_history: bool = False,
    dir_tmp: str | Path = None,
) -> pd.DataFrame | None:
    """Download EUA Primary Auction from the EEX website and extract the data
    into a DataFrame.

    Args:
        fn_out (str | Path | None): The path where the extracted data should be saved as CSV.
            If None, the data will not be saved to a file.
        download_history (bool): Whether to also download the historical data ZIP file.
        dir_tmp (str | Path): The directory where the temporary files should be saved.
            If None the default directory will be used (./data/source/automatic).

    Returns:
        A DataFrame with the extracted auction price data, or None if no data was
        extracted.

    Raises:
        ValueError: If no valid data is extracted from the downloaded files.
    """
    if dir_tmp is None:
        dir_tmp = settings.DIR_SOURCE_AUTOMATIC
    fn_xls, fn_zip = download_auction_reports(
        download_history=download_history, dir_out=dir_tmp
    )
    df = extract_data(fn_xls) if fn_xls else None
    if download_history and fn_zip:
        df_zip = extract_data(fn_zip)
        df = pd.concat([df, df_zip], ignore_index=True) if df is not None else df_zip
    if df is None or df.empty:
        raise ValueError("No valid data extracted from the downloaded files")
    df = parse_auctions(df) if df is not None else None

    if fn_out is not None and df is not None:
        fn_out = Path(fn_out)
        fn_out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(fn_out, index=False)
    return df
