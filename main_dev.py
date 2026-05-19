import os

from dotenv import load_dotenv

from eutl_scraper import Settings
from eutl_scraper.logger import setup_logging
from eutl_scraper.other.locations import (
    # get_installation_coordinates_osm,
    # load_installations,
    pipeline_installation_coordinates,
)

if __name__ == "__main__":
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")
    # extract_installations(settings=settings, save_to_disk=True)
    # create_ets2_installations(settings=settings)
    load_dotenv(".env")

    api_keys = {
        # "googlemaps": os.getenv("GOOGLE_API_KEY"),
        "geoapify": os.getenv("GEOAPIFY_API_KEY"),
        "osm": os.getenv("OSM_USER_AGENT"),
    }
    # df_locations = pipeline_installation_coordinates(
    #     settings=settings,
    #     api_keys=api_keys,
    #     save_to_disk=True,
    # )

    # df_installations = load_installations(
    #     fn=settings.fp("installations", settings.dir_extracted),
    #     max_installations=10,
    # )
    # df_coordinates = get_installation_coordinates_osm(df_installations=df_installations)
    df_coordinates = pipeline_installation_coordinates(
        settings=settings,
        api_keys=api_keys,
        save_to_disk=False,
        max_installations=10,
    )
    print("here")
