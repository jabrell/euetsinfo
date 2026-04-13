from pathlib import Path

from eutl_scraper.settings import Settings

from .account_holders import extract_account_holders
from .accounts import extract_accounts
from .compliance import extract_compliance
from .installations import extract_installations
from .transactions import extract_transactions

__all__ = [
    "extract_compliance",
    "extract_installations",
    "extract_projects",
    "extract_transactions",
    "extract_accounts",
    "extract_account_holders",
]


def extract_all(settings: Settings, fn_manual_account_data: Path) -> None:
    """Extract all EUTL data given the source data

    Args:
        settings (Settings): The settings object containing configuration values.
        fn_manual_account_data (Path): Path to the manual account data Excel file.
    """
    extract_installations(settings=settings)
    extract_compliance(settings=settings)
    extract_transactions(settings=settings)
    extract_accounts(settings=settings)
    extract_account_holders(
        settings=settings,
        fn_manual_account_data=fn_manual_account_data,
    )
