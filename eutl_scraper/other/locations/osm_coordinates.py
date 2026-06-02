import time

import pandas as pd
import requests
from loguru import logger
from tqdm import tqdm

from .geoapify_coordinates import build_full_address

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "euetsinfo"  # Required by OSM to identify your application


def geocode_address_osm(
    address: str,
    user_agent: str = USER_AGENT,
    base_url: str = NOMINATIM_URL,
    timeout: int = 30,
) -> tuple[float | None, float | None]:
    """
    Geocode a single address using the OSM Nominatim API.

    Args:
        address (str): The full address string to geocode.
        user_agent (str): A custom string identifying your application
            (Required by OSM).
        base_url (str): Base URL for the Nominatim geocoding endpoint.
        timeout (int): Request timeout in seconds.
            Defaults to 30 seconds.

    Returns:
        tuple[float | None, float | None]: A tuple (lat, lon) where both elements
            are floats or None if not found.
    """
    if pd.isna(address) or not address.strip():
        return None, None

    params = {
        "q": address,
        "limit": 1,
        "format": "json",
    }

    headers = {"User-Agent": user_agent}

    response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    if not data:
        return None, None

    res = data[0]

    # Nominatim returns strings for coordinates, so we cast to float
    lat = float(res.get("lat"))
    lon = float(res.get("lon"))
    return lat, lon


def get_installation_coordinates_osm(
    df_installations: pd.DataFrame,
    api_key: str,
    rate_limit_seconds: float = 1,
) -> pd.DataFrame:
    """Gets installation coordinates using OSM Nominatim API

    Args:
        df_installations (pd.DataFrame): dataframe with installation data
        api_key (str): API key or user agent for OSM (Nominatim) geocoding.
            Note that OSM does not require an API key, but you must provide a
            user agent string. Naming is intentional to keep the same function
            signature as other geocoding services.
        rate_limit_seconds (float, optional): delay between api calls to respect
            rate limits.
            Default: 1 to be safe against OSM's 1 req/sec limit.

    Returns:
        pd.DataFrame: with installation_id, latitude and longitude
    """
    rows = df_installations.to_dict("records")
    logger.info(f"Fetch locations for {len(rows)} installations from OSM (Nominatim)")

    lst_res = []
    cache: dict[str, tuple[float | None, float | None]] = {}

    for row in tqdm(rows):
        # Assuming build_full_address from your Geoapify script is available
        address = build_full_address(row)

        if not address:
            continue

        # Check cache first to avoid redundant API hits and waits
        if address in cache:
            lat, lon = cache[address]
        else:
            try:
                lat, lon = geocode_address_osm(address, user_agent=api_key)
                cache[address] = (lat, lon)
                # Only sleep if we actually made a network request
                time.sleep(rate_limit_seconds)
            except Exception as exc:
                logger.error(f"Failed to geocode {address}: {exc}")
                continue

        if lat and lon:
            lst_res.append(
                {
                    "installation_id": row["installation_id"],
                    "latitude": lat,
                    "longitude": lon,
                }
            )

    df_loc = pd.DataFrame(lst_res)
    logger.info(f"Retrieved locations for {len(df_loc)} installations from OSM.")
    df_loc = df_loc.assign(created_at=pd.Timestamp.now())
    return df_loc
