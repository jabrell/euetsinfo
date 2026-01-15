import time
from typing import Any

import pandas as pd
import requests
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
    addr1 = clean_part(row.get("address_1"))
    addr2 = clean_part(row.get("address_2"))

    if addr1:
        parts.append(addr1)
    if addr2:
        parts.append(addr2)

    # Location details
    postal_code = clean_part(row.get("postal_code"))
    city = clean_part(row.get("city"))
    country = clean_part(row.get("country"))

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
    timeout: int = 10,
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


def geocode_installations(
    input_csv: str,
    output_csv: str,
    output_coordinates_csv: str,
    api_key: str,
    rate_limit_seconds: float = 0.25,
) -> None:
    """
    Main processing function that reads installations, geocodes their addresses,
    and writes full and coordinates-only CSV outputs.

    Steps:
    - Load input CSV
    - Ensure 'lat' and 'lon' columns exist
    - Build full address strings
    - Filter out certain activity types (10 and 50)
    - Geocode missing coordinates (with a cache to avoid duplicate calls)
    - Save the enriched dataset and a coordinates-only CSV

    Args:
        input_csv: Path to the input CSV file with installations.
        output_csv: Path to the output CSV file with full data (including lat/lon).
        output_coordinates_csv: Path to the output CSV file with only ID and coordinates.
        api_key: Geoapify API key used for geocoding.
        rate_limit_seconds: Delay between API calls to respect rate limits.
    """
    # --- Load CSV ---
    df = pd.read_csv(input_csv)

    # Ensure columns exist
    for col in ["lat", "lon"]:
        if col not in df.columns:
            df[col] = None

    # Build full address for each row
    df["full_address"] = df.apply(build_full_address, axis=1)

    # Filter out activity types 10 and 50
    df = df[df["activity_type_code"] != 10]
    df = df[df["activity_type_code"] != 50]

    # Optional cache to avoid duplicate calls
    cache: dict[str, tuple[float | None, float | None]] = {}

    new_rows: list[dict[str, Any]] = []
    coordinates_rows: list[dict[str, Any]] = []

    try:
        for row in tqdm(df.to_dict("records")):
            # exclude activity types 10 and 50 (aviation and shipping)
            if str(row.get("activity_type_code")) in ["10", "50"]:
                continue

            address = row.get("full_address", "")

            if address in cache:
                lat, lon = cache[address]
            else:
                try:
                    lat, lon = geocode_address(address, api_key=api_key)
                    cache[address] = (lat, lon)
                    time.sleep(rate_limit_seconds)  # rate-limit safety
                except Exception as exc:  # noqa: BLE001
                    print(f"✖ Failed: {address} → {exc}")
                    continue

            new_rows.append(
                {
                    **row,
                    "lat": lat,
                    "lon": lon,
                }
            )
            coordinates_rows.append(
                {
                    "installation_id": row.get("installation_id"),
                    "lat": lat,
                    "lon": lon,
                }
            )
            print(f"✔ Geocoded: {address}")
    except Exception as exc:  # noqa: BLE001
        print(exc)
        print("Exiting...")
    finally:
        # --- Save result ---
        pd.DataFrame(new_rows).to_csv(output_csv, index=False)
        pd.DataFrame(coordinates_rows).to_csv(output_coordinates_csv, index=False)

    print("Done.")
