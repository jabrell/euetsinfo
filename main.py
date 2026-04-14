import os
from pathlib import Path

from dotenv import load_dotenv

from eutl_scraper import Pipelines, Settings, get_all_data, setup_logging

if __name__ == "__main__":
    # path to the manual accounts file
    fn_manual_accounts = Path("manual_data") / "accounts_20260412.xlsx"
    # extract_all(dir_data=Path("data/"), fn_manual_account_data=fn_manual_accounts)
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")
    # load environment variables from .env fil: GEOAPIFY_API_KEY
    load_dotenv()
    GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")

    get_all_data(
        settings=settings,
        pipelines=[
            Pipelines.EUTL,
            Pipelines.NACE_FROM_LEAKAGE_LISTS,
            Pipelines.EEX_AUCTIONS,
            Pipelines.INSTALLATION_COORDINATES,
        ],
        fn_manual_accounts=fn_manual_accounts,
        geoapify_api_key=GEOAPIFY_API_KEY,
        # max_installations=10,
    )
