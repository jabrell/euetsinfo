import logging
from pathlib import Path

import pandas as pd
from frictionless import Package, Report

from eutl_scraper.eutl.extract_new import extract_all
from eutl_scraper.publish import (
    TABLE_REGISTRY,
    create_data_package,
    create_resource,
    prepare_table,
)


def publish_data_package(
    dir_source: str | Path, fn_out: str | Path, validate_package: bool = False
) -> tuple[Package, Report | None]:
    """Create and save a frictionlessdata package from the given input directory
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
        logging.info(f"Processing {table_name} from {path}...")
        print(f"Create resources for {table_name} from {path}...")
        df_source = pd.read_csv(path, low_memory=False)
        df = prepare_table(table_config=config, df=df_source)
        resource = create_resource(table_config=config, df=df)
        logging.info(f"Resource for {table_name} created successfully.")
        resources.append(resource)

    # create the data package
    print("Creating data package...")
    logging.info("Creating data package with all resources...")
    package = create_data_package(
        resources=resources, fn_out=fn_out, name="eutl_data_package"
    )
    report = None
    if validate_package:
        logging.info("Validating the created data package...")
        my_package = Package(fn_out)
        report = my_package.validate()
        if not report.valid:
            for task in report.tasks:
                if not task.valid:
                    logging.error(
                        f"Resource '{task.name}': "
                        f"{task.stats['errors']} errors found."
                        "Check the validation report for details."
                    )
        else:
            logging.info("Data package validated successfully.")
    return package, report


if __name__ == "__main__":
    # dir_source = Path("data/extracted")
    # fn_out = Path("test.zip")
    # package, report = publish_data_package(
    #     dir_source=dir_source, fn_out=fn_out, validate_package=True
    # )
    dir_source = Path("data/source/")
    dir_extracted = Path("data/extracted/")
    fn_direct = dir_source / "eutl_accounts.csv"
    fn_trans = dir_source / "eutl_transactions.csv"
    fn_manual_accounts = Path("data/manual/") / "accounts.xlsx"
    extract_all(dir_data=Path("data/"), fn_manual_account_data=fn_manual_accounts)
    print("here")
