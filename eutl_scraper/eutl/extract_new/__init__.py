from pathlib import Path

from eutl_scraper.settings import Settings

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
]


def extract_all(dir_data: Path) -> None:
    """Extract all EUTL data given the source data

    Args:
        dir_data (Path): Data directory. This points to the root of the data
            directory (e.g. /data/)
    """
    settings = Settings(dir_data=dir_data)
    extract_installations(settings=settings)
    extract_compliance(settings=settings)
    extract_transactions(settings=settings)
    extract_accounts(settings=settings)
