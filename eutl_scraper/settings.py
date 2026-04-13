from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import httpx

DIR_DATA = Path(__file__).parent / "data"

DIR_SOURCE = DIR_DATA / "source"
DIR_SOURCE_AUTOMATIC = DIR_SOURCE

DIR_EXTRACTED = DIR_DATA / "extracted"
DIR_NORMALIZED = DIR_DATA / "normalized"


@dataclass
class Settings:
    dir_data: Path = DIR_DATA

    FILENAMES: ClassVar[dict[str, str]] = {
        "accounts": "eutl_accounts",
        "installations": "eutl_installations",
        "compliance": "eutl_compliance",
        "transactions": "eutl_transactions",
        "projects": "eutl_projects",
        "account_holders": "eutl_account_holders",
        "link_accounts_holders": "eutl_link_accounts_holders",
        "eex_auctions": "eex_auctions",
        "nace_from_leakage_lists": "nace_from_leakage_lists",
        "nace_scheme": "nace_scheme",
    }

    def __post_init__(self):
        self.dir_data = Path(self.dir_data)

        self.client = httpx.Client(
            timeout=httpx.Timeout(60.0, read=300.0),
            limits=httpx.Limits(max_keepalive_connections=5),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
            },
        )

    @property
    def dir_source(self) -> Path:
        """Directory containing the source data files downloaded"""
        return self.dir_data / "source"

    @property
    def dir_extracted(self) -> Path:
        """Directory containing the extracted datafiles"""
        return self.dir_data / "extracted"

    def fp(self, key: str, directory: Path, ending: str = "csv") -> Path:
        """Get the file path for the given key and directory.

        Example usage
            settings = Settings(data_dir="/test/")
            settings.fp("accounts", settings.dir_source)

        Args:
            key (str): Key for the filename
                see settings.FILENAMES for valid keys.
            directory (Path): Directory to which the filename should be appended.
            ending (str): File extension to append to the filename.
                Default is "csv".

        Returns:
            Path with the full path to the file corresponding to the given key
                and directory.
        """
        fn = self.FILENAMES.get(key)
        if fn is None:
            raise KeyError(f"Key {key} not found in FILENAMES.")
        return directory / f"{fn}.{ending}"

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
