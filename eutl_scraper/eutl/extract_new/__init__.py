from pathlib import Path

from eutl_scraper.settings import Settings

from .compliance import extract_compliance
from .installations import extract_installations

__all__ = ["extract_compliance", "extract_installations"]


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
