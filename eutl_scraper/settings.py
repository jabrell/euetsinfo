import io
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import httpx
import pandas as pd
from loguru import logger


@dataclass
class Settings:
    """Central configuration object passed to every pipeline and bundle.

    `Settings` is the single source of truth for **where data lives**. Every
    pipeline resolves its file paths through `Settings` — never by
    constructing paths manually — so that the on-disk layout can be
    reorganised by changing this one class.

    **On-disk layout**

    Under a single root `dir_data`, the framework maintains two stage
    directories that are created automatically on construction:

    - `dir_source` (`<dir_data>/source`): raw artefacts as they arrive
      from a remote source or as supplied by the user. Files here are
      typically untouched copies of upstream data (gzipped CSVs that have
      been decompressed in-flight, ZIP-embedded CSVs, byte-copied Excel
      files, etc.). This is the **input directory for extract pipelines**.
    - `dir_extracted` (`<dir_data>/extracted`): cleaned, normalised tables
      ready for publication. This is the **output directory for extract
      and augment pipelines** and the input directory for the publication
      layer.

    **Stable internal filenames**

    The class-level `FILENAMES` dictionary maps an **internal key** (e.g.
    `"accounts"`, `"compliance"`, `"transactions"`) to a **stable
    basename** (e.g. `"eutl_accounts"`). Pipelines use these keys to refer
    to files; the basenames never change at runtime. Renames go through
    `FILENAMES` so every producer and consumer stays in sync.

    **Path resolution**

    Two methods resolve paths from internal keys:

    - `fp(key, directory, ending="csv")` — path to an automatically
      managed file (in `dir_source` or `dir_extracted`). The basename is
      looked up in `FILENAMES` and joined with `directory` and `ending`.
      Use this for everything the framework writes.
    - `fp_manual(key)` — path to a **user-supplied** file. The user
      provides these paths at construction via the `manual_files`
      argument; this method returns the registered external path.

    **Manual files**

    Some entities depend on artefacts that the framework cannot download
    automatically — the user either exports them by hand from a portal or
    maintains them as a local cache. The class-level `MANUAL_FILES`
    dictionary enumerates every known manual-file key and a one-line
    description of what it is for. `manual_files` provided at construction
    must use a subset of these keys; an unknown key raises `ValueError`.

    Currently known manual files:

    - `"manual_accounts"` — PowerBI accounts export (XLSX). Required by
      `AccountHoldersBundle` for the holder identity data the public Azure
      blob does not expose.
    - `"existing_installation_locations"` — user-maintained cache of
      previously-geocoded installation coordinates (CSV with at least
      `installation_id` and `source` columns). Optional input to
      `InstallationLocationsBundle`; suppresses redundant geocoding API
      calls when present.

    Example:

    ```python
    Settings(
        dir_data=Path("./data"),
        manual_files={
            "manual_accounts": Path("manual_data/accounts_20260412.xlsx"),
            "existing_installation_locations": Path(
                "manual_data/installation_locations.csv"
            ),
        },
    )
    ```

    For `manual_accounts`, a dedicated `Fetch*ManualPipeline` byte-copies
    the user-supplied file into `dir_source` under its stable internal
    name, so downstream extract pipelines find it via the regular `fp`
    lookup. For `existing_installation_locations`, the user-owned cache
    file is read directly from its external path at extract time.

    Args:
        dir_data: Root directory under which `dir_source` and
            `dir_extracted` are managed.
        manual_files: Mapping from a key in `MANUAL_FILES` to a
            user-supplied external file path. Defaults to an empty dict.
            Required for bundles that depend on a manual file (e.g.
            `AccountsBundle`). Unknown keys raise `ValueError`.

    Raises:
        ValueError: If `manual_files` contains a key not declared in
            `MANUAL_FILES`.
    """

    dir_data: Path
    manual_files: dict[str, Path] = field(default_factory=dict)

    FILENAMES: ClassVar[dict[str, str]] = {
        "accounts": "eutl_accounts",
        "installations": "eutl_installations",
        "link_installation_account": "eutl_link_installation_account",
        "compliance": "eutl_compliance",
        "transactions": "eutl_transactions",
        "projects": "eutl_projects",
        "account_holders": "eutl_account_holders",
        "link_account_holder": "eutl_link_account_holder",
        "eex_auctions": "eex_auctions",
        "nace_from_leakage_lists": "nace_from_leakage_lists",
        "nace_scheme": "nace_scheme",
        "installation_locations": "installation_locations",
        "existing_installation_locations": "existing_installation_locations",
        "manual_accounts": "eutl_manual_accounts",
    }

    # Keys accepted in ``manual_files`` and what each manual file is for.
    # Anything passed in ``manual_files`` that is not a key here triggers a
    # ``ValueError`` at construction.
    MANUAL_FILES: ClassVar[dict[str, str]] = {
        "manual_accounts": (
            "PowerBI accounts export (XLSX). Required by AccountHoldersBundle "
            "for holder identity data not exposed via the public Azure blob."
        ),
        "existing_installation_locations": (
            "User-maintained cache of previously-geocoded installation "
            "coordinates (CSV with at least installation_id and source "
            "columns). Optional input to InstallationLocationsBundle; "
            "suppresses redundant geocoding API calls when present."
        ),
    }

    def __post_init__(self):
        self.dir_data = Path(self.dir_data)

        # validate manual_files keys against the documented allow-list
        unknown = set(self.manual_files) - set(self.MANUAL_FILES)
        if unknown:
            raise ValueError(
                f"Unknown manual_files key(s): {sorted(unknown)}. "
                f"Valid keys are: {sorted(self.MANUAL_FILES)}."
            )

        # create directories if they don't exist
        self.dir_source.mkdir(parents=True, exist_ok=True)
        self.dir_extracted.mkdir(parents=True, exist_ok=True)

    @property
    def dir_source(self) -> Path:
        """Directory containing the source data files downloaded"""
        return self.dir_data / "source"

    @property
    def dir_extracted(self) -> Path:
        """Directory containing the extracted datafiles"""
        return self.dir_data / "extracted"

    def fp_manual(self, key: str) -> Path:
        """Resolve the path to a user-supplied manual file by internal key.

        Args:
            key: Internal key (one of `MANUAL_FILES`) identifying which
                manual file is needed.

        Returns:
            The user-supplied external path for that file.

        Raises:
            KeyError: If no path has been registered for `key` in
                `manual_files`.
        """
        if key not in self.manual_files:
            raise KeyError(
                f"No manual file configured for '{key}'. "
                f"Provide via Settings(manual_files={{'{key}': Path(...)}})."
            )
        return Path(self.manual_files[key])

    def fp(self, key: str, directory: Path, ending: str = "csv") -> Path:
        """Get the file path for the given key and directory.

        Example:

        ```python
        settings = Settings(dir_data="/test/")
        settings.fp("accounts", settings.dir_source)
        ```

        Args:
            key: Key for the filename; see `FILENAMES` for valid keys.
            directory: Directory to which the filename should be appended.
            ending: File extension to append to the filename. Defaults to
                `"csv"`.

        Returns:
            The full path to the file corresponding to the given key and
            directory.

        Raises:
            KeyError: If `key` is not in `FILENAMES`.
        """
        fn = self.FILENAMES.get(key)
        if fn is None:
            raise KeyError(
                f"Key {key} not found in FILENAMES."
                f"Valid keys are: {list(self.FILENAMES.keys())}"
            )
        return directory / f"{fn}.{ending}"


class DownloadClient:
    def __init__(self, **overrides):
        """HTTP client for downloading data with automatic resume on connection drop.

        Args:
            overrides: Keyword arguments to override the default httpx.Client settings.
                See httpx.Client for available settings.
        """
        defaults = dict(
            timeout=httpx.Timeout(120.0, read=300.0),
            limits=httpx.Limits(max_keepalive_connections=5),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
            },
        )
        defaults.update(overrides)
        self._client = httpx.Client(**defaults)

    def download_csv(
        self, url: str, fn_out: Path | None = None, **read_csv_kwargs
    ) -> pd.DataFrame:
        """Download a (possibly gzipped) CSV via client and return it as a DataFrame.

        Args:
            url: URL to download from.
            fn_out: If provided, save the resulting CSV here.
            **read_csv_kwargs: Forwarded to pd.read_csv.

        Returns:
            DataFrame with the downloaded data.
        """
        buf = self.download_with_resume(url)
        df = pd.read_csv(buf, compression="gzip", **read_csv_kwargs)
        logger.info(f"Downloaded {len(df)} rows from {url}", filter="download_csv")
        if fn_out is not None:
            df.to_csv(fn_out, index=False)
        return df

    def download_with_resume(
        self, url: str, chunk_size: int = 1024 * 1024, attempts: int = 10
    ) -> io.BytesIO:
        """Download data with automatic resume on connection drop.

        Args:
            url (str): URL to download data from.
            chunk_size (int): Size of chunks to download at a time (in bytes).
                Default is 1 MB.
            attempts (int): Number of attempts to retry downloading on failure.
                Default is 10.

        Returns:
            io.BytesIO: Buffer containing the downloaded data."""
        buffer = io.BytesIO()
        buffer = io.BytesIO()
        for attempt in range(attempts):
            downloaded = buffer.tell()
            headers = {}
            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"
                logger.info("Resuming from {:.1f} MB...", downloaded / 1e6)
            try:
                with self._client.stream("GET", url, headers=headers) as response:
                    if response.status_code == 416:
                        break
                    for chunk in response.iter_bytes(chunk_size=chunk_size):
                        buffer.write(chunk)
                break
            except httpx.RemoteProtocolError:
                wait = 2 ** (attempt + 1)
                logger.warning("Connection dropped, resuming in {}s...", wait)
                time.sleep(wait)
        else:
            raise RuntimeError(f"Failed to download {url} after {attempts} attempts")
        buffer.seek(0)
        return buffer

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
