import pandas as pd
from pathlib import Path

from eutl_scraper import download, extract, download_and_normalize_data
from eutl_scraper.nace_assignments import extract_nace_by_installation
from eutl_scraper.extract_accounts import create_account_table_with_holders


def extract_tables(dir_normalized: str, dir_out: str) -> None:
    """Extract the basic tables from the normalized EUTL data.

    Args:
        dir_normalized (str): Directory containing the normalized data.
        dir_out (str): Directory to save the extracted tables.
    """
    # installations
    df_installations = pd.read_csv(f"{dir_normalized}/eutl_installations.csv")
    fn_out = f"{dir_out}/eutl_installations.csv"
    extract.installations(df_installations, fn_out=fn_out)

    # compliance
    df_compliance = pd.read_csv(f"{dir_normalized}/eutl_compliance.csv")
    fn_out = f"{dir_out}/eutl_compliance.csv"
    extract.compliance(df_compliance, fn_out=fn_out)

    # transactions
    df_transactions = pd.read_csv(f"{dir_normalized}/eutl_transactions.csv")
    extract.transactions(df_transactions, dir_out=dir_out)


if __name__ == "__main__":
    dir_source = Path("data/source")
    dir_out = Path("data/extracted")
    dir_normalized = Path("data/normalized")
    dir_extracted = Path("data/extracted")

    # download and normalize data
    download.all_data(dir_out=dir_source / "automatic")
    download_and_normalize_data(dir_out=dir_normalized)
    extract_tables(dir_normalized=dir_normalized, dir_out=dir_extracted)

    # based on the extracted tables, create the account table with holders
    create_account_table_with_holders(
        fn_direct=dir_source / "automatic" / "eutl_accounts.csv",
        fn_bi=dir_source / "manual" / "accounts.xlsx",
        fn_trans=dir_source / "automatic" / "eutl_transactions.csv",
        dir_out=dir_out,
    )

    # extract NACE classifications by installation
    extract_nace_by_installation(
        fn_out=dir_out / "nace_by_installation.csv",
        fn_leakage_2015=dir_source / "manual" / "leakage_2015.xlsx",
        fn_leakage_2020=dir_source / "manual" / "leakage_2020.xlsx",
    )
    # print("done")
