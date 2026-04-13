from enum import StrEnum
from functools import partial
from pathlib import Path

from eutl_scraper.settings import Settings

from .eex_auctions import pipeline_eex_auctions
from .eutl import pipeline_eutl
from .locations import pipeline_installation_coordinates
from .nace_codes import pipeline_nace_from_leakage_lists


class Pipelines(StrEnum):
    EUTL = "eutl"
    INSTALLATION_COORDINATES = "installation_coordinates"
    NACE_FROM_LEAKAGE_LISTS = "nace_from_leakage_lists"
    EEX_AUCTIONS = "eex_auctions"


PIPELINE_REGISTRY: dict[Pipelines, callable] = {
    Pipelines.EUTL: pipeline_eutl,
    Pipelines.NACE_FROM_LEAKAGE_LISTS: pipeline_nace_from_leakage_lists,
    Pipelines.EEX_AUCTIONS: pipeline_eex_auctions,
    Pipelines.INSTALLATION_COORDINATES: pipeline_installation_coordinates,
}


def get_all_data(
    settings: Settings,
    pipelines: list[Pipelines] | None = None,
    fn_manual_accounts: str | Path | None = None,
    geoapify_api_key: str | None = None,
    max_installations: int | None = None,
) -> None:
    """Run the specified pipelines to get all data.

    Args:
        pipelines (list[Pipelines] | None): List of pipelines to run.
            If None, all pipelines will be run.
            Possible pipelines are:
            - Pipelines.EUTL: Download and extract EUTL data.
            - Pipelines.NACE_FROM_LEAKAGE_LISTS: Extract NACE codes from the leakage
                lists.
            - Pipelines.EEX_AUCTIONS: Download and extract EEX auction data.
            - Pipelines.INSTALLATION_COORDINATES: Extract installation coordinates.
        fn_manual_accounts (str | Path | None): Filename of the manually downloaded
            account data. This is only needed for the EUTL pipeline.
            If None, an error will be raised if the EUTL pipeline is run.
        geoapify_api_key (str | None): API key for the Geoapify geocoding service.
            This is only needed for the INSTALLATION_COORDINATES pipeline.
        max_installations (int | None): Optional limit on the number of installations to
            process in the INSTALLATION_COORDINATES pipeline (useful for testing).
            If None, all installations will be processed.
    """
    if pipelines is None:
        pipelines = list(Pipelines)

    # kwargs shared by all pipelines
    kwargs = {}
    kwargs["settings"] = settings

    # build a local registry with any pipeline-specific overrides
    registry = dict(PIPELINE_REGISTRY)
    if fn_manual_accounts is not None:
        registry[Pipelines.EUTL] = partial(
            pipeline_eutl, fn_manual_accounts=fn_manual_accounts
        )
    if Pipelines.INSTALLATION_COORDINATES in pipelines:
        registry[Pipelines.INSTALLATION_COORDINATES] = partial(
            pipeline_installation_coordinates,
            api_key=geoapify_api_key,
            max_installations=max_installations,
        )

    for pipeline in pipelines:
        print(f"------ Running {pipeline.value} pipeline...")
        registry[pipeline](**kwargs)
