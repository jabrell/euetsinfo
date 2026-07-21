"""Top-level entry point for building the Frictionless Data Package.

`publish_data_package` reads every published table from
`Settings.dir_extracted`, runs each through `prepare_table` and
`create_resource`, and writes the resulting bundle to disk via
`create_data_package`. Optional whole-package validation is delegated to
the Frictionless library.
"""

from pathlib import Path

import pandas as pd
from frictionless import Package, Report
from loguru import logger

from eutl_scraper import Settings

from .prepare_tables import prepare_table
from .resources import create_data_package, create_resource
from .table_registry import TABLE_REGISTRY


def publish_data_package(
    settings: Settings, fn_out: str | Path, validate_package: bool = False
) -> tuple[Package, Report | None]:
    """Create and save a frictionless data package from the given input directory
    containing the extracted CSV files.

    Args:
        settings (Settings): Settings object containing configuration.
        fn_out (str | Path): Output filename for the created data package (ZIP file).
        validate_package (bool): Whether to validate the created data package.
            Defaults to False. If True, the created package will be validated
            using the frictionless data library and any validation errors will be
            logged.

    Returns:
        tuple[Package, Report | None]: The created data package and the validation
            report (if validation is enabled).
    """
    data_paths = {
        "installations": settings.fp(
            "installations", settings.dir_extracted, ending="parquet"
        ),
        "accounts": settings.fp("accounts", settings.dir_extracted, ending="parquet"),
        "link_installation_account": settings.fp(
            "link_installation_account", settings.dir_extracted, ending="parquet"
        ),
        "account_holders": settings.fp(
            "account_holders", settings.dir_extracted, ending="parquet"
        ),
        "link_account_holder": settings.fp(
            "link_account_holder", settings.dir_extracted, ending="parquet"
        ),
        "compliance": settings.fp(
            "compliance", settings.dir_extracted, ending="parquet"
        ),
        "projects": settings.fp("projects", settings.dir_extracted, ending="parquet"),
        "transactions": settings.fp(
            "transactions", settings.dir_extracted, ending="parquet"
        ),
        "installation_locations": settings.fp(
            "installation_locations", settings.dir_extracted, ending="parquet"
        ),
        "nace_mappings": settings.fp(
            "nace_from_leakage_lists", settings.dir_extracted, ending="parquet"
        ),
        # exclude the EEX auction data due to licensing issues
        # "eex_auctions": settings.fp(
        #     "eex_auctions", settings.dir_extracted, ending="parquet"
        # ),
        "powerplants": settings.fp(
            "powerplants", settings.dir_extracted, ending="parquet"
        ),
        "map_installation_to_plant": settings.fp(
            "map_installation_to_plant", settings.dir_extracted, ending="parquet"
        ),
        "map_installation_to_eid_facility": settings.fp(
            "map_installation_to_eid_facility", settings.dir_extracted, ending="parquet"
        ),
        "map_entsoe_to_plant": settings.fp(
            "map_entsoe_to_plant", settings.dir_extracted, ending="parquet"
        ),
        "map_orbis": settings.fp("map_orbis", settings.dir_extracted, ending="parquet"),
    }

    # loop over the tables, prepare the data and create resources
    resources = []
    for table_name, path in data_paths.items():
        config = TABLE_REGISTRY[table_name]
        logger.info(
            f"Processing {table_name} from {path}...", filter="publish_data_package"
        )
        print(f"Create resources for {table_name} from {path}...")
        df_source = pd.read_parquet(path)
        df = prepare_table(table_config=config, df=df_source)
        resource = create_resource(table_config=config, df=df)
        logger.info(
            f"Resource for {table_name} created successfully.",
            filter="publish_data_package",
        )
        resources.append(resource)

    # create the data package
    logger.info(
        "Creating data package with all resources...", filter="publish_data_package"
    )
    package = create_data_package(
        resources=resources, fn_out=fn_out, name="eutl_data_package"
    )
    report = None
    if validate_package:
        logger.info("Validating the created data package...")
        my_package = Package(fn_out)
        report = my_package.validate()
        if not report.valid:
            for task in report.tasks:
                if not task.valid:
                    logger.error(
                        f"Resource '{task.name}': "
                        f"{task.stats['errors']} errors found."
                        "Check the validation report for details."
                    )
        else:
            logger.info("Data package validated successfully.")
    return package, report
