import pandas as pd

from eutl_scraper import download_and_normalize_data, extract


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
    dir_normalized = "data/normalized"
    dir_extracted = "data/extracted"
    download_and_normalize_data(dir_out=dir_normalized)
    extract_tables(dir_normalized=dir_normalized, dir_out=dir_extracted)
    print("done")
