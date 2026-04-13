from pathlib import Path

import pandas as pd
from frictionless import Package, Report
from loguru import logger

from eutl_scraper import Pipelines, get_all_data
from eutl_scraper.logger import setup_logging
from eutl_scraper.publish import (
    TABLE_REGISTRY,
    create_data_package,
    create_resource,
    prepare_table,
)
from eutl_scraper.settings import Settings


def publish_data_package(
    dir_source: str | Path, fn_out: str | Path, validate_package: bool = False
) -> tuple[Package, Report | None]:
    """Create and save a frictionless data package from the given input directory
    containing the extracted CSV files.

    Args:
        dir_source (str | Path): Directory containing the extracted CSV files.
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
        "installations": dir_source / "eutl_installations.csv",
        "accounts": dir_source / "eutl_accounts.csv",
        "holders": dir_source / "eutl_account_holders.csv",
        "compliance": dir_source / "eutl_compliance.csv",
        "projects": dir_source / "eutl_projects.csv",
        "transactions": dir_source / "eutl_transactions.csv",
        "installation_locations": dir_source / "installation_locations.csv",
        "nace_mappings": dir_source / "nace_from_leakage_lists.csv",
        "eex_auctions": dir_source / "eex_auctions.csv",
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
    # dir_source = Path("data/extracted")
    # fn_out = Path("test.zip")
    # package, report = publish_data_package(
    #     dir_source=dir_source, fn_out=fn_out, validate_package=True
    # )
    # dir_source = Path("data/source/")
    # dir_extracted = Path("data/extracted/")
    # fn_direct = dir_source / "eutl_accounts.csv"
    # fn_trans = dir_source / "eutl_transactions.csv"
    fn_manual_accounts = Path("data/manual/") / "accounts.xlsx"
    # extract_all(dir_data=Path("data/"), fn_manual_account_data=fn_manual_accounts)
    settings = Settings(dir_data="data/")
    setup_logging("INFO")
    get_all_data(
        settings=settings,
        pipelines=[
            # Pipelines.EUTL,
            Pipelines.NACE_FROM_LEAKAGE_LISTS,
            Pipelines.EEX_AUCTIONS,
            # Pipelines.INSTALLATION_COORDINATES,
        ],
        fn_manual_accounts=fn_manual_accounts,
    )
    print("here")
