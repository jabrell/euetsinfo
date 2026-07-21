import os

from dotenv import load_dotenv

from eutl_scraper import Settings
from eutl_scraper.other.eex_auctions.bundle import EEXAuctionsBundle
from eutl_scraper.logger import setup_logging

if __name__ == "__main__":
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")
    EEXAuctionsBundle(
        settings=settings,
    ).run()
    print("here")
