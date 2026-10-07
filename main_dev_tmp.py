from eutl_scraper import Settings
from eutl_scraper.eutl.accounts import ExtractAccountsPipeline
from eutl_scraper.eutl.add_missing_accounts_from_transactions import (
    AddMissingAccountsFromTransactionsPipeline,
)
from eutl_scraper.eutl.transactions import ExtractTransactionsPipeline
from eutl_scraper.logger import setup_logging

if __name__ == "__main__":
    # raw inputs already in data_tmp/source: eutl_accounts.csv,
    # eutl_manual_accounts.xlsx, eutl_transactions.csv -> no fetch needed
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")

    # 1. transactions (registry/account ids of EU parties)
    ExtractTransactionsPipeline(settings=settings).run()
    # 2. downloaded accounts + manual accounts (rebuilds accounts from scratch)
    ExtractAccountsPipeline(settings=settings).run()
    # 3. + accounts only seen in transactions
    AddMissingAccountsFromTransactionsPipeline(settings=settings).run()
    print("here")
