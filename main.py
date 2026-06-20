import os
from pathlib import Path

from dotenv import load_dotenv

from eutl_scraper import AllDataBundle, Settings, setup_logging

if __name__ == "__main__":
    # path to the manual accounts file
    fn_manual_accounts = Path("manual_data") / "accounts_20260620.xlsx"

    # settings and logging
    settings = Settings(
        dir_data="data_tmp/",
        manual_files={
            "manual_accounts": fn_manual_accounts,
            "existing_installation_locations": Path(
                "manual_data/coordinates_geoapify.csv"
            ),
        },
    )
    setup_logging("INFO")

    # load environment variables from .env file: API keys for geocoding
    load_dotenv()
    api_keys = {
        # "googlemaps": os.getenv("GOOGLE_API_KEY"),
        "geoapify": os.getenv("GEOAPIFY_API_KEY"),
        # "osm": os.getenv("OSM_USER_AGENT"),
    }

    AllDataBundle(
        settings=settings,
        api_keys=api_keys,
    ).run()

    print("here")
