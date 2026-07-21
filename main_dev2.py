import os
from pathlib import Path
from dotenv import load_dotenv

from eutl_scraper import Settings, AllDataBundle
from eutl_scraper.eutl.accounts import AccountsBundle, ExtractAccountsPipeline
from eutl_scraper.eutl.add_missing_accounts_from_transactions import (
    AddMissingAccountsFromTransactionsPipeline,
)
from eutl_scraper.logger import setup_logging

if __name__ == "__main__":
    settings = Settings(
        dir_data="data_tmp/",
        manual_files={
            "manual_accounts": Path("manual_data/accounts_20260721.xlsx"),
            "existing_installation_locations": Path("manual_data/installation_locations.csv"),
        })
    setup_logging("INFO")
    # ExtractAccountsPipeline(settings=settings).run()
    AddMissingAccountsFromTransactionsPipeline(settings=settings).run()
    print("here")
