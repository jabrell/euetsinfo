from pathlib import Path

import pandas as pd
from frictionless import Package, Report
from loguru import logger

from eutl_scraper import Settings

# from eutl_scraper.eutl.extract.installations import extract_installations
from eutl_scraper.logger import setup_logging
from eutl_scraper.publish import (
    TABLE_REGISTRY,
    create_data_package,
    create_resource,
    prepare_table,
)


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
        "installations": settings.fp("installations", settings.dir_extracted),
        "accounts": settings.fp("accounts", settings.dir_extracted),
        "link_installation_account": settings.fp(
            "link_installation_account", settings.dir_extracted
        ),
        "account_holders": settings.fp("account_holders", settings.dir_extracted),
        "link_account_holder": settings.fp(
            "link_account_holder", settings.dir_extracted
        ),
        "compliance": settings.fp("compliance", settings.dir_extracted),
        "projects": settings.fp("projects", settings.dir_extracted),
        "transactions": settings.fp("transactions", settings.dir_extracted),
        "installation_locations": settings.fp(
            "installation_locations", settings.dir_extracted
        ),
        "nace_mappings": settings.fp("nace_from_leakage_lists", settings.dir_extracted),
        "eex_auctions": settings.fp("eex_auctions", settings.dir_extracted),
    }

    # loop over the tables, prepare the data and create resources
    resources = []
    for table_name, path in data_paths.items():
        config = TABLE_REGISTRY[table_name]
        logger.info(
            f"Processing {table_name} from {path}...", filter="publish_data_package"
        )
        print(f"Create resources for {table_name} from {path}...")
        df_source = pd.read_csv(path, low_memory=False)
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


if __name__ == "__main__":
    settings = Settings(dir_data="data_tmp/")
    setup_logging("INFO")
    # extract_installations(settings=settings, save_to_disk=True)
    package, report = publish_data_package(
        settings=settings, fn_out="test.zip", validate_package=True
    )
    print("here")
