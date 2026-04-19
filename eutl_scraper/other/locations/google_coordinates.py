import googlemaps
import pandas as pd

from eutl_scraper.eutl.mappings import map_registryCodes


def form_address(row: pd.Series) -> tuple[str, str]:
    """Forms address based on Series with address data

    Args:
        row (pd.Series): with address data, including mainAddress, secondaryAddress,
            postalCode, city and country.

    Returns:
        tuple[str, str]: address and country code
    """
    address = ""
    for a in ["mainAddress", "secondaryAddress", "postalCode", "city", "country"]:
        if pd.notnull(row[a]):
            if a == "country":
                address += f"{map_registryCodes.get(row[a])}, "
            else:
                address += f"{row[a]}, "
    if len(address) > 0:
        address = address[:-2]
    return address, row["country"]


def get_gmaps_coordinates(
    gmaps: googlemaps.Client, address: str, countryCode: str | None = None
):
    """Get latitude and longitude from google maps

    Args:
        gmaps (googlemaps.Client): google maps client
        address (str): address
        countryCode (str | None): two digit iso code of the country. If provided,
            the search will be limited to this country. This can help to get
            more accurate results for countries with overseas territories.

    """
    # get locations
    # for countries with oversea teritores exclude the country identifier
    if countryCode in ["FR", "GB", "NL", "DK", "NO"]:
        loc = gmaps.geocode(address=address)
    else:
        loc = gmaps.geocode(address=address, components={"country": countryCode})
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
) -> pd.DataFrame:
    """Gets installation coordinates using googlemaps api

    Args:
        df_installations (pd.DataFrame): dataframe with installation data
        api_key (str): google api key

    Returns:
        pd.DataFrame: with installation_id, latitude and longitude
    """
    # get installation data, excluding aircrafts
    mask = ~df_installations["activity"].isin(
        ["10-Aircraft operator activities", "50-Maritime operator activities"]
    )
    df_in = df_installations[mask]

    # google client
    gmaps = googlemaps.Client(key=api_key)

    # loop over installations, get address and coordinates
    lst_res = []
    print(f"Fetch locations for {len(df_in)} installations")
    for i, (_, row) in enumerate(df_in.iterrows()):
        if ((i + 1) % 500) == 0:
            print(
                "Get GoogleMaps coordinates for installation %s (%d/%d)"
                % (row["installationID"], (i + 1), len(df_in))
            )
        address, countryCode = form_address(row)
        lat, lng = get_gmaps_coordinates(gmaps, address, countryCode=countryCode)
        if lat:
            res = {}
            res["installation_id"] = row["installationID"]
            res["latitude"] = lat
            res["longitude"] = lng
            lst_res.append(res)
    df_loc = pd.DataFrame(lst_res)
    print(f"Retrieved locations for {len(df_loc)} installations. ")

    return df_loc
