from pathlib import Path

from eutl_scraper.settings import Settings

from .compliance import extract_compliance
from .installations import extract_installations
from .transactions import extract_projects, extract_transactions

__all__ = [
    "extract_compliance",
    "extract_installations",
    "extract_projects",
    "extract_transactions",
]


def extract_all(dir_data: Path) -> None:
    """Extract all EUTL data given the source data

    Args:
        dir_data (Path): Data directory. This points to the root of the data
            directory (e.g. /data/)
    """
    settings = Settings(dir_data=dir_data)
    extract_installations(
        fn_source=settings.fp("installations", settings.dir_source),
        fn_out=settings.fp("installations", settings.dir_extracted),
    )
    extract_compliance(
        fn_source=settings.fp("compliance", settings.dir_source),
        fn_out=settings.fp("compliance", settings.dir_extracted),
    )
    extract_transactions(
        fn_source=settings.fp("transactions", settings.dir_source),
        fn_out=settings.fp("transactions", settings.dir_extracted),
    )
    extract_projects(
        fn_source=settings.fp("transactions", settings.dir_source),
        fn_out=settings.fp("projects", settings.dir_extracted),
    )
