import os

from dotenv import load_dotenv

from eutl_scraper.settings import Settings, DownloadClient
from eutl_scraper.eutl.union_registry_scrapers import resolve_download_url
from eutl_scraper.logger import setup_logging

if __name__ == "__main__":
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")
    url = resolve_download_url("Transactions", DownloadClient())
    print(url)

    print("here")
