import pandas as pd

from eutl_scraper import download, extract_base_table, normalize


def create_installation_base_table(fn_out: str | None = None) -> pd.DataFrame:
    """Create the installation table by downloading, normalizing, and
    extracting installation data.

    Args:
        fn_out (str | None, optional): Output filename to save the installation data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing installation data.
    """
    df = (
        download.installations()
        .pipe(normalize.installations)
        .pipe(extract_base_table.installations, fn_out=fn_out)
    )
    return df


def create_compliance_base_table(fn_out: str | None = None) -> pd.DataFrame:
    """Create the compliance table by downloading, normalizing, and
    extracting compliance data.

    Args:
        fn_out (str | None, optional): Output filename to save the compliance data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing compliance data.
    """
    df = (
        download.compliance()
        .pipe(normalize.compliance)
        .pipe(extract_base_table.compliance, fn_out=fn_out)
    )
    return df


def create_transaction_table(fn_out: str | None = None) -> pd.DataFrame:
    """Create the transaction table by downloading, normalizing, and
    extracting transaction data.

    Args:
        fn_out (str | None, optional): Output filename to save the transaction data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing transaction data.
    """
    df = pd.read_csv("data/source/automatic/eutl_transactions.csv", low_memory=False)
    df = (
        # download.transactions()
        df.pipe(normalize.transactions)
        # .pipe(extract_base_table.transactions, fn_out=fn_out)  # Uncomment if extraction function exists
    )
    return df


def download_and_normalize_data(dir_out: str) -> None:
    """Download and normalize all datasets: compliance, installations, and transactions.

    Args
        dir_out (str): Directory to save the normalized data.
    """
    # Installations
    df_installations = download.installations().pipe(normalize.installations)
    df_installations.to_csv(f"{dir_out}/eutl_installations.csv", index=False)
    # Compliance
    df_compliance = download.compliance().pipe(normalize.compliance)
    df_compliance.to_csv(f"{dir_out}/eutl_compliance.csv", index=False)
    # Transactions
    df_transactions = download.transactions().pipe(normalize.transactions)
    df_transactions.to_csv(f"{dir_out}/eutl_transactions.csv", index=False)
    return None


if __name__ == "__main__":
    dir_extracted = "data/extracted"
    # df_installations = create_installation_base_table(
    #     fn_out=f"{dir_extracted}/eutl_installations.csv"
    # )
    # df_compl = create_compliance_base_table(
    #     fn_out=f"{dir_extracted}/eutl_compliance.csv"
    # )
    # df_trans = create_transaction_table(fn_out=f"{dir_extracted}/eutl_transactions.csv")
    download_and_normalize_data(dir_out="data/normalized")
    print("done")
