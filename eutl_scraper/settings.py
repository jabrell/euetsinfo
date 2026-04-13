import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import httpx
from loguru import logger


@dataclass
class Settings:
    dir_data: Path

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
        "installation_locations": "installation_locations",
    }

    def __post_init__(self):
        self.dir_data = Path(self.dir_data)

        # create directories if they don't exist
        self.dir_source.mkdir(parents=True, exist_ok=True)
        self.dir_extracted.mkdir(parents=True, exist_ok=True)

        self.client = httpx.Client(
            timeout=httpx.Timeout(120.0, read=300.0),
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

    def download_with_resume(
        self, url: str, chunk_size: int = 1024 * 1024, attempts: int = 5
    ) -> io.BytesIO:
        """Download data with automatic resume on connection drop.

        Args:
            url (str): URL to download data from.
            chunk_size (int): Size of chunks to download at a time (in bytes).
                Default is 1 MB.
            attempts (int): Number of attempts to retry downloading on failure.
                Default is 5.

        Returns:
            io.BytesIO: Buffer containing the downloaded data."""
        buffer = io.BytesIO()

        for attempt in range(attempts):
            downloaded = buffer.tell()
            headers = {}

            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"
                logger.info("Resuming download from {:.1f} MB...", downloaded / 1e6)

            try:
                with self.client.stream("GET", url, headers=headers) as response:
                    if response.status_code == 416:
                        break
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        buffer.write(chunk)

                break  # success

            except httpx.RemoteProtocolError:
                wait = 2 ** (attempt + 1)
                logger.warning("Connection dropped, resuming in {}s...", wait)
                time.sleep(wait)
        else:
            raise RuntimeError(f"Failed to download {url} after {attempts} attempts")

        buffer.seek(0)
        return buffer
