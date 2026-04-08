import os
from pathlib import Path

from dotenv import load_dotenv

from eutl_scraper import Pipelines, get_all_data

if __name__ == "__main__":
    # path to the manual accounts file
    fn_manual_accounts = Path(__file__).parent / "data" / "manual" / "accounts.xlsx"

    # load environment variables from .env fil: GEOAPIFY_API_KEY
    load_dotenv()
    GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")

    # if the pipelines argument is None, all pipelines will be run
    get_all_data(
        pipelines=[
            Pipelines.EUTL,
            Pipelines.NACE_FROM_LEAKAGE_LISTS,
            Pipelines.EEX_AUCTIONS,
            # Pipelines.INSTALLATION_COORDINATES,
        ],
        fn_manual_accounts=fn_manual_accounts,
        geoapify_api_key=GEOAPIFY_API_KEY,
    )
