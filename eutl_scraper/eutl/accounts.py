"""Accounts data flow.

Four classes covering the accounts entity end-to-end:

- :class:`FetchAccountsPipeline` — downloads the raw accounts CSV from the
  EUTL public Azure blob and writes it to ``dir_source``.
- :class:`FetchManualAccountsPipeline` — byte-copies the user-supplied
  PowerBI accounts Excel from ``dir_manual`` to ``dir_source`` so downstream
  pipelines (today: none; future: account-holders extract) can find it via
  the standard ``settings.fp(...)`` path.
- :class:`ExtractAccountsPipeline` — reads the raw accounts CSV from
  ``dir_source``, cleans and normalises it, and writes the result to
  ``dir_extracted``.
- :class:`AccountsBundle` — flat bundle of the three pipelines above.

This module is self-contained for its helper logic — cleaning helpers live
here as static methods on :class:`ExtractAccountsPipeline`, not imported from
elsewhere.
"""

import pandas as pd

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import DownloadClient, Settings


class FetchAccountsPipeline(Pipeline):
    """Download the raw EUTL accounts CSV from the EUTL public Azure blob.

    Inputs:
        Remote URL: the EUTL accounts daily snapshot, served as a gzipped CSV
        from the EU's public Azure blob storage.

    Product:
        The raw accounts table as a single DataFrame (gzip already
        decompressed in-flight by ``DownloadClient.download_csv``).

    Output location:
        ``settings.fp("accounts", settings.dir_source)`` — i.e. the
        ``eutl_accounts.csv`` file under ``dir_source``.
    """

    name = "fetch_accounts"
    URL = (
        "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/"
        "extracts/_all_extracts/account/accounts_daily.csv.gz"
    )

    def __init__(self, settings: Settings, client: DownloadClient | None = None):
        """Initialise the pipeline.

        Args:
            settings (Settings): Configuration object used to resolve the
                output path via ``settings.fp("accounts", dir_source)``.
            client (DownloadClient, optional): Shared HTTP client to reuse
                across multiple fetch pipelines. If ``None``, the pipeline
                creates and closes its own.
        """
        super().__init__(settings)
        self._client = client

    def load(self) -> None:
        own_client = self._client is None
        client = self._client or DownloadClient()
        try:
            self.df = client.download_csv(url=self.URL)
        finally:
            if own_client:
                client.close()

    def transform(self) -> None:
        # identity: the raw CSV is the product of a fetch pipeline
        pass

    def save(self) -> None:
        self.df.to_csv(
            self.settings.fp("accounts", self.settings.dir_source), index=False
        )


class FetchManualAccountsPipeline(Pipeline):
    """Copy the user-supplied PowerBI accounts Excel into dir_source.

    Inputs:
        A user-placed Excel file. The path is supplied by the user via
        ``Settings(manual_files={"manual_accounts": Path(...)})`` and looked
        up here through ``settings.fp_manual("manual_accounts")``. The file
        is not modified or parsed in this pipeline — it is moved verbatim
        into ``dir_source`` so it can be picked up by downstream extract
        pipelines using the standard ``settings.fp(...)`` lookup.

    Product:
        The raw Excel bytes, untouched.

    Output location:
        ``settings.fp("manual_accounts", settings.dir_source, ending="xlsx")``.
    """

    name = "fetch_manual_accounts"

    def load(self) -> None:
        self._bytes = self.settings.fp_manual("manual_accounts").read_bytes()

    def transform(self) -> None:
        # identity: the Excel is moved verbatim
        pass

    def save(self) -> None:
        dst = self.settings.fp(
            "manual_accounts", self.settings.dir_source, ending="xlsx"
        )
        dst.write_bytes(self._bytes)


class ExtractAccountsPipeline(Pipeline):
    """Clean and normalise the raw EUTL accounts CSV into the published shape.

    Inputs:
        Raw accounts CSV produced by :class:`FetchAccountsPipeline`, read
        from ``settings.fp("accounts", settings.dir_source)``. The fetch
        pipeline (or any equivalent that places this file on disk) must have
        run first; this pipeline does no remote calls.

    Product:
        The cleaned accounts table — composite ``account_id`` from registry
        code and account identifier, renamed columns, unified
        ``account_type`` (combining ``ETS_ACCOUNT_TYPE`` and ``FULL_TYPE``),
        boolean ``isClosurePending``, and a ``created_at`` stamp.

    Output location:
        ``settings.fp("accounts", settings.dir_extracted, ending="parquet")``
        — i.e. the ``eutl_accounts.parquet`` file under ``dir_extracted``.
    """

    name = "extract_accounts"

    _COLUMN_MAP: dict[str, str] = {
        "account_id": "account_id",
        "registry_code": "registry_id",
        "ACCOUNT_NAME": "accountName",
        "OPEN_DATE": "openingDate",
        "END_OF_VALIDITY_DATE": "closingDate",
        "IS_CLOSURE_PENDING": "isClosurePending",
        "SNAPSHOT_DATE": "snapshotDate",
    }

    def load(self) -> None:
        self.df = pd.read_csv(self.settings.fp("accounts", self.settings.dir_source))

    def transform(self) -> None:
        self.df = (
            self.df.pipe(self._strip_str)
            .pipe(self._clean_and_create_ids)
            .pipe(self._rename_and_check)
            .assign(created_at=pd.Timestamp.now())
        )

    def save(self) -> None:
        self.df.to_parquet(
            self.settings.fp("accounts", self.settings.dir_extracted, ending="parquet"),
            index=False,
        )

    @staticmethod
    def _strip_str(df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace from string columns.

        Args:
            df (pd.DataFrame): Input DataFrame.

        Returns:
            pd.DataFrame: DataFrame with whitespace stripped from string columns.
        """
        df = df.copy()
        str_cols = df.select_dtypes(include=["object", "string"]).columns
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip())
        return df

    @staticmethod
    def _clean_and_create_ids(df: pd.DataFrame) -> pd.DataFrame:
        """Create unique account IDs from registry code and account identifier.

        Args:
            df (pd.DataFrame): DataFrame containing raw accounts data
                (already whitespace-stripped).

        Returns:
            pd.DataFrame: DataFrame with an added ``account_id`` column.
        """
        return df.assign(
            account_id=lambda df: (
                df["REGISTRY_CODE"] + "_" + df["ACCOUNT_IDENTIFIER"].astype(str)
            ),
        )

    @classmethod
    def _rename_and_check(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns, unify account type, and convert closure flag to boolean.

        Args:
            df (pd.DataFrame): DataFrame containing accounts data after
                ID creation.

        Returns:
            pd.DataFrame: DataFrame containing accounts in the published
                shape.
        """
        df_accounts = df.rename(columns=cls._COLUMN_MAP).drop(
            columns=["REGISTRY_NAME", "ACCOUNT_IDENTIFIER", "REGISTRY_CODE"]
        )
        df_accounts = df_accounts.assign(
            account_type=(
                lambda df: df["ETS_ACCOUNT_TYPE"].combine_first(df["FULL_TYPE"])
            )
        ).drop(columns=["ETS_ACCOUNT_TYPE", "FULL_TYPE", "ACCOUNT_TYPE"])
        df_accounts = df_accounts.assign(
            isClosurePending=lambda df: df["isClosurePending"] == "Y"
        )
        return df_accounts


class AccountsBundle(Bundle):
    """Accounts entity end-to-end: Azure download, manual Excel copy, extract.

    Data flow:

    - **FetchAccountsPipeline**

      - Input: remote gzipped CSV from the EUTL public Azure blob.
      - Output: ``dir_source/eutl_accounts.csv`` (gzip decompressed
        in-flight; written as plain CSV).

    - **FetchManualAccountsPipeline**

      - Input: user-supplied PowerBI Excel at
        ``settings.fp_manual("manual_accounts")`` (path registered by the
        user via ``Settings(manual_files=...)``).
      - Output: ``dir_source/eutl_manual_accounts.xlsx`` (byte-for-byte
        copy under the stable internal name).
      - Fails loud with ``KeyError`` if no ``"manual_accounts"`` entry is
        in ``Settings.manual_files``, or ``FileNotFoundError`` if the path
        does not exist.

    - **ExtractAccountsPipeline**

      - Input: ``dir_source/eutl_accounts.csv``.
      - Output: ``dir_extracted/eutl_accounts.parquet`` (cleaned accounts
        table).

    Run this bundle on its own to produce the published accounts table and
    stage the manual Excel for downstream account-holders extraction.
    """

    name = "eutl_accounts"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            FetchAccountsPipeline(self.settings),
            FetchManualAccountsPipeline(self.settings),
            ExtractAccountsPipeline(self.settings),
        ]
