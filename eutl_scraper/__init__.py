from . import download, extract, normalize
from .fetch_coordinates import geocode_installations

__all__ = [
    "download",
    "normalize",
    "extract",
    "download_and_normalize_data",
    "geocode_installations",
]


def download_and_normalize_data(dir_out: str) -> None:
    """Download and normalize all datasets: compliance, installations, and transactions.

    Args:
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
