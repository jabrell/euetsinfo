"""Module to fetch coordinates for EUTL installations based on the
[Geoapify API](https://www.geoapify.com/).

The first version of this module was provided by: Roberto Rossini (Bruegel)"""

import time
from typing import Any

import pandas as pd
import requests
from loguru import logger
from tqdm import tqdm

GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/search"


def clean_part(value: Any) -> str | None:
    """
    Clean a single address component.

    - Converts the value to string
    - Strips whitespace
    - Returns None for NaN, empty strings, or '-'.

    Args:
        value: The raw value from the DataFrame row.

    Returns:
        The cleaned string or None if the value is considered empty.
    """
    if pd.isna(value):
        return None
    value_str = str(value).strip()
    if value_str == "" or value_str == "-":
        return None
    return value_str


def build_full_address(row: dict) -> str:
    """
    Build a full address string from a row containing address parts.

    The function expects the row to have the following keys/columns:
    - 'address_1'
    - 'address_2'
    - 'postal_code'
    - 'city'
    - 'country'

    Args:
        row: A pandas Series or dictionary-like object representing a row.

    Returns:
        A single comma-separated address string.
    """
    parts: list[str] = []

    # Address lines
    addr1 = clean_part(row.get("address1"))
    addr2 = clean_part(row.get("address2"))

    if addr1:
        parts.append(addr1)
    if addr2:
        parts.append(addr2)

    # Location details
    postal_code = clean_part(row.get("postal_code"))
    city = clean_part(row.get("city"))
    country = clean_part(row.get("registry_name"))

    city_block = ", ".join(part for part in (postal_code, city) if part)
    if city_block:
        parts.append(city_block)

    if country:
        parts.append(country)

    return ", ".join(parts)


def geocode_address(
    address: str,
    api_key: str,
    base_url: str = GEOAPIFY_URL,
    timeout: int = 30,
) -> tuple[float | None, float | None]:
    """
    Geocode a single address using the Geoapify API.

    Args:
        address: The full address string to geocode.
        api_key: Geoapify API key.
        base_url: Base URL for the Geoapify geocoding endpoint.
        timeout: Request timeout in seconds.

    Returns:
        A tuple (lat, lon) where both elements are floats or None if not found.
    """
    if pd.isna(address) or not address.strip():
        return None, None

    params = {
        "text": address,
        "limit": 1,
        "format": "json",
        "apiKey": api_key,
    }

    response = requests.get(base_url, params=params, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    if not data.get("results"):
        return None, None

    res = data["results"][0]
    lat = res.get("lat")
    lon = res.get("lon")
    return lat, lon


def get_installation_coordinates_geoapify(
    df_installations, api_key, rate_limit_seconds=1
):
    """Gets installation coordinates using geoapify api

    Args:
        df_installations (pd.DataFrame): dataframe with installation data
        api_key (str): geoapify api key
        rate_limit_seconds (float, optional): delay between api calls to respect
            rate limits.
            Defaults to 1.

    Returns:
        pd.DataFrame: with installation_id, latitude and longitude
    """
    rows = df_installations.to_dict("records")
    logger.info(f"Fetch locations for {len(rows)} installations from geoapify")
    lst_res = []
    for row in tqdm(rows):
        address = build_full_address(row)
        try:
            lat, lon = geocode_address(address, api_key=api_key)
            time.sleep(rate_limit_seconds)
        except Exception as exc:
            logger.error(f"Failed to geocode {address}: {exc}")
            continue
        if lat and lon:
            res = {}
            res["installation_id"] = row["installation_id"]
            res["latitude"] = lat
            res["longitude"] = lon
            lst_res.append(res)
    df_loc = pd.DataFrame(lst_res)
    logger.info(f"Retrieved locations for {len(df_loc)} installations from geoapify.")
    df_loc = df_loc.assign(created_at=pd.Timestamp.now())
    return df_loc
