import os

import dotenv

from eutl_scraper.locations import pipeline_installation_coordinates

if __name__ == "__main__":
    # Load environment variables from .env file
    dotenv.load_dotenv()
    # --- Configuration / constants section ---
    # add your Geoapify API key to a .env file in the project root
    # Alternatively, set it manually here but avoid committing it to version control
    GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "")

    pipeline_installation_coordinates(
        api_key=GEOAPIFY_API_KEY, rate_limit_seconds=0.25, max_installations=50
    )
