"""Module for downloading the current and historical auction price data from the
EEX website."""

import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ...settings import Settings

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}
EEX_URL = "https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download"

# patterns to match the relevant XLSX and ZIP files based on their naming convention
# on the EEX website.
XLSX_PATTERN = re.compile(
    r"emission-spot-primary-market-auction-report-\d{4}-data\.xlsx$", re.IGNORECASE
)
ZIP_PATTERN = re.compile(
    r"emission-spot-primary-market-auction-report-.*data\.zip$", re.IGNORECASE
)


def download_auction_reports(
    settings: Settings, download_history: bool = False
) -> tuple[Path | None, Path | None]:
    """Download the current auction price data (XLSX) and optionally the historical
    data (ZIP) from the EEX website.

    Args:
        settings (Settings): The settings object containing configuration values.
        download_history: Whether to download the historical data ZIP file.

    Returns:
        A tuple of (xlsx_path, zip_path) where each is a Path to the downloaded
        file or None if the corresponding file was not found or downloaded.
    """
    xlsx_url, zip_url = find_first_xlsx_and_zip(EEX_URL)

    xlsx_path = None
    zip_path = None

    if xlsx_url:
        xlsx_path = settings.fp("eex_auctions", settings.dir_source, ending="xlsx")
        download_file(xlsx_url, xlsx_path)
    else:
        raise ValueError("Could not find XLSX URL on the page")

    if download_history and zip_url:
        zip_path = settings.fp("eex_auctions", settings.dir_source, ending="zip")
        download_file(zip_url, zip_path)

    return xlsx_path, zip_path


def download_file(url: str, dest_path: str | Path):
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
    resp = requests.get(page_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    xlsx_url = None
    zip_url = None

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()

        if xlsx_url is None and XLSX_PATTERN.search(href):
            xlsx_url = urljoin(page_url, href)
        elif zip_url is None and ZIP_PATTERN.search(href):
            zip_url = urljoin(page_url, href)

        if xlsx_url and zip_url:
            break

    if xlsx_url is None:
        raise FileNotFoundError(f"No XLSX link found on {page_url}")

    return xlsx_url, zip_url
