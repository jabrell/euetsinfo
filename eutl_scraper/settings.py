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

    ``Settings`` is the single source of truth for **where data lives**. Every
    pipeline resolves its file paths through ``Settings`` — never by
    constructing paths manually — so that the on-disk layout can be reorganised
    by changing this one class.

    On-disk layout
    --------------
    Under a single root ``dir_data``, the framework maintains two stage
    directories that are created automatically on construction:

    - ``dir_source`` (``<dir_data>/source``): raw artifacts as they arrive
      from a remote source or as supplied by the user. Files here are
      typically untouched copies of upstream data (gzipped CSVs that have
      been decompressed in-flight, ZIP-embedded CSVs, byte-copied Excel
      files, etc.). This is the **input directory for extract pipelines**.
    - ``dir_extracted`` (``<dir_data>/extracted``): cleaned, normalised
      tables ready for publication. This is the **output directory for
      extract and augment pipelines** and the input directory for the
      publication layer.

    Stable internal filenames
    -------------------------
    The class-level ``FILENAMES`` dictionary maps an **internal key** (e.g.
    ``"accounts"``, ``"compliance"``, ``"transactions"``) to a **stable
    basename** (e.g. ``"eutl_accounts"``). Pipelines use these keys to refer
    to files; the basenames never change at runtime. Renames go through
    ``FILENAMES`` so every producer and consumer stays in sync.

    Path resolution
    ---------------
    Two methods resolve paths from internal keys:

    - :meth:`fp(key, directory, ending="csv")` — path to an automatically
      managed file (in ``dir_source`` or ``dir_extracted``). The basename
      is looked up in ``FILENAMES`` and joined with ``directory`` and
      ``ending``. Use this for everything the framework writes.
    - :meth:`fp_manual(key)` — path to a **user-supplied** file (e.g. the
      PowerBI accounts Excel). The user provides these paths at
      construction via the ``manual_files`` argument; this method returns
      the registered external path.

    Manual files
    ------------
    Some entities (today: account holders) depend on artifacts that the
    framework cannot download automatically — the user exports them by hand
    from a portal and saves them somewhere on their machine. The
    ``manual_files`` dict maps the same internal key used in ``FILENAMES``
    to the user's real external path::

        Settings(
            dir_data=Path("./data"),
            manual_files={
                "manual_accounts": Path("manual_data/accounts_20260412.xlsx")
            },
        )

    A dedicated ``Fetch*ManualPipeline`` byte-copies the user-supplied file
    into ``dir_source`` under its stable internal name, so downstream
    extract pipelines find it via the regular :meth:`fp` lookup.

    Args:
        dir_data (Path): Root directory under which ``dir_source`` and
            ``dir_extracted`` are managed.
        manual_files (dict[str, Path], optional): Mapping from internal
            ``FILENAMES`` keys to user-supplied external file paths.
            Defaults to an empty dict. Required for bundles that include a
            manual-fetch pipeline (e.g. :class:`AccountsBundle`).
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
        "manual_accounts": "eutl_manual_accounts",
    }

    def __post_init__(self):
        self.dir_data = Path(self.dir_data)

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
            key (str): Internal key (matching a ``FILENAMES`` key) identifying
                which manual file is needed.

        Returns:
            Path: The user-supplied external path for that file.

        Raises:
            KeyError: If no path has been registered for ``key`` in
                ``manual_files``.
        """
        if key not in self.manual_files:
            raise KeyError(
                f"No manual file configured for '{key}'. "
                f"Provide via Settings(manual_files={{'{key}': Path(...)}})."
            )
        return Path(self.manual_files[key])

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
