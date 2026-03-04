import os
from pathlib import Path

import dotenv

from eutl_scraper import geocode_installations

if __name__ == "__main__":
    # Load environment variables from .env file
    dotenv.load_dotenv()
    # --- Configuration / constants section ---
    # add your Geoapify API key to a .env file in the project root
    # Alternatively, set it manually here but avoid committing it to version control
    GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")

    # todo: move paths to own config file
    CURRENT_PATH = Path(__file__).resolve()
    DATA_PATH = CURRENT_PATH.parent / "data" / "extracted"
    INPUT_CSV = DATA_PATH / "eutl_installations.csv"
    OUTPUT_CSV = DATA_PATH / "eutl_installations-output.csv"
    OUTPUT_COORDINATES_CSV = DATA_PATH / "eutl_installations_coordinates.csv"

    geocode_installations(
        input_csv=INPUT_CSV,
        output_csv=OUTPUT_CSV,
        output_coordinates_csv=OUTPUT_COORDINATES_CSV,
        api_key=GEOAPIFY_API_KEY,
        rate_limit_seconds=0.25,
    )
