import os
from pathlib import Path

from dotenv import load_dotenv

from eutl_scraper import Pipelines, Settings, get_all_data, setup_logging

if __name__ == "__main__":
    # path to the manual accounts file
    fn_manual_accounts = Path("manual_data") / "accounts_20260412.xlsx"

    # settings and logging
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")

    # load environment variables from .env file: API keys for geocoding
    load_dotenv()
    api_keys = {
        "googlemaps": os.getenv("GOOGLE_API_KEY"),
        "geoapify": os.getenv("GEOAPIFY_API_KEY"),
    }

    get_all_data(
        settings=settings,
        pipelines=[
            Pipelines.EUTL,
            Pipelines.NACE_FROM_LEAKAGE_LISTS,
            Pipelines.EEX_AUCTIONS,
            Pipelines.INSTALLATION_COORDINATES,
        ],
        fn_manual_accounts=fn_manual_accounts,
        api_keys=api_keys,
    )
