import os
from pathlib import Path
from dotenv import load_dotenv

from eutl_scraper import Settings
from eutl_scraper.eutl import EUTLBundle
from eutl_scraper.other.eex_auctions import EEXAuctionsBundle
from eutl_scraper.other.nace_codes import  NaceFromLeakageListsBundle
from eutl_scraper.other.locations import InstallationLocationsBundle
from eutl_scraper.logger import setup_logging

if __name__ == "__main__":
    settings = Settings(
        dir_data="data_tmp/",
        manual_files={
            "manual_accounts": Path("manual_data/accounts_20260412.xlsx"),
            "existing_installation_locations": Path("manual_data/installation_locations.csv"),
        })
    setup_logging("INFO")
    # extract_installations(settings=settings, save_to_disk=True)
    # create_ets2_installations(settings=settings)
    load_dotenv(".env")

    api_keys = {
        "googlemaps": os.getenv("GOOGLE_API_KEY"),
        "geoapify": os.getenv("GEOAPIFY_API_KEY"),
        "osm": os.getenv("OSM_USER_AGENT"),
    }
    # df_locations = pipeline_installation_coordinates(
    #     settings=settings,
    #     api_keys=api_keys,
    #     save_to_disk=True,
    # )
    # EUTLBundle(settings=settings).run()
    # EEXAuctionsBundle(settings=settings).run()
    # NaceFromLeakageListsBundle(settings=settings, drop_missing_installations=True).run()
    InstallationLocationsBundle(settings=settings, api_keys=api_keys, max_installations=30).run()

    print("here")
