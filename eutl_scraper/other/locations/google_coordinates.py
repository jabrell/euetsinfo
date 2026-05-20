import googlemaps
import pandas as pd
from loguru import logger
from tqdm import tqdm

from eutl_scraper.eutl.mappings import map_registryCodes


def form_address(row: pd.Series) -> tuple[str, str]:
    """Forms address based on Series with address data

    Args:
        row (pd.Series): with address data, including address1, address2,
            postal_code, city and registry_id.

    Returns:
        tuple[str, str]: address and registry code
    """
    address = ""
    for a in ["address1", "address2", "postal_code", "city", "registry_id"]:
        if pd.notnull(row[a]):
            if a == "registry_id":
                address += f"{map_registryCodes.get(row[a])}, "
            else:
                address += f"{row[a]}, "
    if len(address) > 0:
        address = address[:-2]
    return address, row["registry_id"]


def get_gmaps_coordinates(
    gmaps: googlemaps.Client, address: str, registryCode: str | None = None
):
    """Get latitude and longitude from google maps

    Args:
        gmaps (googlemaps.Client): google maps client
        address (str): address
        registryCode (str | None): registry code. If provided,
            the search will be limited to this registry. This can help to get
            more accurate results for countries with overseas territories.

    """
    # get locations
    # for countries with oversea teritores exclude the country identifier
    if registryCode in ["FR", "GB", "NL", "DK", "NO"]:
        loc = gmaps.geocode(address=address)
    else:
        loc = gmaps.geocode(address=address, components={"country": registryCode})
    # if get no results, try without countryCode to include overseas territories
    if len(loc) == 0:
        loc = gmaps.geocode(address=address)

    # in case of multiple matches, we take the first one
    if len(loc) > 0:
        try:
            return tuple(loc[0]["geometry"]["location"].values())
        except KeyError:
            pass
    return None, None


def get_installation_coordinates_google(
    df_installations: pd.DataFrame,
    api_key: str,
    rate_limit_seconds: float = 1,
) -> pd.DataFrame:
    """Gets installation coordinates using googlemaps api

    Args:
        df_installations (pd.DataFrame): dataframe with installation data
        api_key (str): google api key
        rate_limit_seconds (float, optional): delay between api calls to respect
            rate limits. Not applicable for googlemaps, but included for consistency
            with other geocoding services.
            Default: 1.

    Returns:
        pd.DataFrame: with installation_id, latitude and longitude
    """
    # google client
    gmaps = googlemaps.Client(key=api_key)

    # loop over installations, get address and coordinates
    lst_res = []
    logger.info(
        f"Fetch locations for {len(df_installations)} installations from google maps"
    )
    for _, row in tqdm(df_installations.iterrows(), total=len(df_installations)):
        address, countryCode = form_address(row)
        lat, lng = get_gmaps_coordinates(gmaps, address, registryCode=countryCode)
        if lat:
            res = {}
            res["installation_id"] = row["installation_id"]
            res["latitude"] = lat
            res["longitude"] = lng
            lst_res.append(res)
    df_loc = pd.DataFrame(lst_res)
    logger.info(
        f"Retrieved locations for {len(df_loc)} installations from google maps."
    )
    df_loc = df_loc.assign(created_at=pd.Timestamp.now())
    return df_loc
