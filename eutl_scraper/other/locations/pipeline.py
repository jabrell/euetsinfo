import concurrent.futures

import pandas as pd
from loguru import logger

from ...settings import Settings
from .geoapify_coordinates import get_installation_coordinates_geoapify
from .google_coordinates import get_installation_coordinates_google
from .osm_coordinates import get_installation_coordinates_osm


def load_installations(
    fn: str,
    max_installations: int | None = None,
) -> pd.DataFrame:
    """Load and prepare the installations data for geocoding.

    Args:
        fn (str): Path to the CSV file containing the installations data.
        max_installations (int, optional): Limit the number of installations to process.
            Defaults to None.

    Returns:
        pd.DataFrame: A DataFrame with the installations data ready for geocoding.
    """
    df = pd.read_csv(fn)

    # do not geocode aircrafts or maritime
    mask = ~df["activity_type_code"].isin([50.0, 10.0, pd.NA])
    df = df[mask]

    # enforce the maximuim number of installations to process (useful for testing)
    if max_installations is not None:
        df = df.head(max_installations)
    return df


def pipeline_installation_coordinates(
    settings: Settings,
    api_keys: dict[str, str],
    save_to_disk: bool = True,
    max_installations: int | None = None,
) -> pd.DataFrame:
    """Download coordinates for all installations in the EUTL dataset.

    Args:
        api_keys: API key for the geocoding service
            Geoapify API key: https://www.geoapify.com/
            For OMS (Nominatim) no API key is needed, but you must provide a
            user agent string.
        save_to_disk (bool): Whether to save the extracted data to disk.
            Defaults to True.
        max_installations: Optional limit on the number of installations to process
            (useful for testing). If None, all installations will be processed.

    Returns:
        A DataFrame with the coordinates for all installations.
    """
    # get and prepare the installation file
    df_installations = load_installations(
        fn=settings.fp("installations", settings.dir_extracted),
        max_installations=max_installations,
    )

    # fetch coordinates and save to disk
    logger.info(
        "Starting installation coordinates pipeline...",
        filter="installation_coordinates_pipeline",
    )
    geocoding_services = {
        "googlemaps": get_installation_coordinates_google,
        "geoapify": get_installation_coordinates_geoapify,
        "osm": get_installation_coordinates_osm,
    }

    # check that only valid services are provided
    for service_name in api_keys.keys():
        if service_name not in geocoding_services:
            raise ValueError(
                f"Invalid geocoding service: {service_name}. "
                f"Valid services are: {list(geocoding_services.keys())}"
            )

    # loop over geocoding services and concatenate results
    lst_df = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(api_keys)) as executor:
        # Submit all tasks to the executor and store the futures in a dictionary
        future_to_service = {}
        for service_name, api_key in api_keys.items():
            if not api_key:
                logger.warning(
                    f"API key/User Agent for {service_name} not found. Skipping..."
                )
                continue
            geocode_func = geocoding_services[service_name]

            # executor.submit runs the function in a separate thread
            future = executor.submit(geocode_func, df_installations, api_key)
            future_to_service[future] = service_name

        # collect the results as they complete
        for future in concurrent.futures.as_completed(future_to_service):
            service_name = future_to_service[future]
            try:
                # Retrieve the resulting DataFrame from the thread
                df_result = future.result()
                lst_df.append(df_result.assign(source=service_name))
                logger.info(f"Successfully completed fetch for {service_name}.")
            except Exception as exc:
                # Catch exceptions from inside the thread so they don't crash
                # the whole pipeline
                logger.error(f"Service {service_name} generated an exception: {exc}")

    # combine results from all services into a single DataFrame
    df = pd.concat(lst_df, ignore_index=True)

    # save to disk
    if save_to_disk:
        logger.info(
            "Saving extracted installation coordinates to disk...",
            filter="installation_coordinates_pipeline",
        )
        fn_out = settings.fp("installation_locations", settings.dir_extracted)
        df.to_csv(fn_out, index=False)

    return df
