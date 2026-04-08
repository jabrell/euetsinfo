import logging
from pathlib import Path

import pandas as pd

from eutl_scraper.publish import (
    TABLE_REGISTRY,
    create_data_package,
    create_resource,
    prepare_table,
)

if __name__ == "__main__":
    dir_source = Path("data/extracted/")
    data_paths = {
        "installations": dir_source / "eutl_installations.csv",
        "accounts": dir_source / "eutl_accounts.csv",
        "holders": dir_source / "eutl_account_holders.csv",
        "compliance": dir_source / "eutl_compliance.csv",
        "projects": dir_source / "eutl_projects.csv",
        "transactions": dir_source / "eutl_transactions.csv",
    }

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

    print("Creating data package...")
    logging.info("Creating data package with all resources...")
    create_data_package(
        resources=resources, fn_out="test.zip", name="eutl_data_package"
    )
    print("Data package created successfully in data/published/")
