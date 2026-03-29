"""Module for downloading the current and historical auction price data from the EEX website."""

from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from eutl_scraper.settings import DIR_SOURCE_AUTOMATIC

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}
EEX_URL = "https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download"


def download_auction_reports(
    dir_out: str | None = None, download_history: bool = False
) -> tuple[Path | None, Path | None]:
    """Download the current auction price data (XLSX) and optionally the historical
    data (ZIP) from the EEX website.

    Args:
        dir_out: The directory where the files should be saved.
            If None the default directory will be used (./data/source/automatic).
        download_history: Whether to download the historical data ZIP file.

    Returns:
        A tuple of (xlsx_path, zip_path) where each is a Path to the downloaded
        file or None if the corresponding file was not found or downloaded.
    """
    dir_out = Path(dir_out) if dir_out else DIR_SOURCE_AUTOMATIC

    xlsx_url, zip_url = find_first_xlsx_and_zip(EEX_URL)

    xlsx_path = None
    zip_path = None

    if xlsx_url:
        xlsx_path = dir_out / "eex_auction_prices.xlsx"
        _download_file(xlsx_url, xlsx_path)
    else:
        raise ValueError("Could not find XLSX URL on the page")

    if download_history and zip_url:
        zip_path = dir_out / "eex_auction_prices_history.zip"
        _download_file(zip_url, zip_path)

    return xlsx_path, zip_path


def _download_file(url: str, dest_path: str):
    """Download a file from a URL and save it to a destination path.

    Args:
        url (str): The URL of the file to download.
        dest_path (str | Path): The path where the file should be saved.

    Raises:
        requests.HTTPError: If the HTTP request returned an unsuccessful status code.
    """
    with requests.get(url, headers=HEADERS, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def find_first_xlsx_and_zip(page_url: str) -> tuple[str | None, str | None]:
    """Find the first XLSX and ZIP links on a webpage. The XLSX is the current
    auction price data and the ZIP is the historical data.

    Args:
        page_url: The URL of the webpage to search.
    """
    # todo narrow to the relevant section of the page instead of searching all links
    resp = requests.get(page_url, headers=HEADERS, timeout=30)
    try:
        resp.raise_for_status()
    except Exception as e:
        raise ValueError(
            f"Failed to fetch page {page_url}: {resp.status_code} {resp.reason}"
        ) from e

    soup = BeautifulSoup(resp.text, "html.parser")

    xlsx_url = None
    zip_url = None

    for a in soup.find_all("a", href=True):
        href_raw = a["href"].strip()
        href = href_raw.lower()

        if href.endswith(".xlsx") and xlsx_url is None:
            xlsx_url = urljoin(page_url, href_raw)
        elif href.endswith(".zip") and zip_url is None:
            zip_url = urljoin(page_url, href_raw)

        if xlsx_url and zip_url:
            break

    return xlsx_url, zip_url
