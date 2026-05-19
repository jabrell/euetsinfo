"""Installations data flow.

Three classes covering the installations entity end-to-end:

- `FetchInstallationsPipeline` — downloads the raw installations CSV from
  the EUTL public Azure blob and writes it to `dir_source`.
- `ExtractInstallationsPipeline` — reads the raw installations CSV from
  `dir_source`, cleans it, and emits two parquet outputs to
  `dir_extracted`: the cleaned installations table and the derived
  installation-account link table.
- `InstallationsBundle` — flat bundle of the two pipelines above.

This module is self-contained for its helper logic — cleaning helpers
live here as static methods on `ExtractInstallationsPipeline`.
"""

import pandas as pd

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import DownloadClient, Settings


class FetchInstallationsPipeline(Pipeline):
    """Download the raw EUTL installations CSV from the EUTL public Azure blob.

    Inputs:
        Remote URL — the EUTL operators daily snapshot, served as a
        gzipped CSV from the EU's public Azure blob storage.

    Product:
        The raw installations table as a single DataFrame (gzip already
        decompressed in-flight by `DownloadClient.download_csv`).

    Output location:
        `settings.fp("installations", settings.dir_source)` — i.e. the
        `eutl_installations.csv` file under `dir_source`.
    """

    name = "fetch_installations"
    URL = (
        "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/"
        "extracts/_all_extracts/operator/operators_daily.csv.gz"
    )

    def __init__(self, settings: Settings, client: DownloadClient | None = None):
        """Initialise the pipeline.

        Args:
            settings: Configuration object used to resolve the output path
                via `settings.fp("installations", dir_source)`.
            client: Shared HTTP client to reuse across multiple fetch
                pipelines. If `None`, the pipeline creates and closes its
                own.
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
            self.settings.fp("installations", self.settings.dir_source), index=False
        )


class ExtractInstallationsPipeline(Pipeline):
    """Clean the raw installations CSV and derive the link table.

    Inputs:
        Raw installations CSV produced by `FetchInstallationsPipeline`,
        read from `settings.fp("installations", settings.dir_source)`.
        The fetch pipeline (or any equivalent that places this file on
        disk) must have run first; this pipeline does no remote calls.

    Product:
        Two cohesive outputs derived from one cleaning pass:

        - The cleaned **installations** table — one row per installation
          with composite `installation_id`, registry IDs, activity
          metadata, address, and snapshot / `created_at` stamps.
        - The **link_installation_account** table mapping
          `installation_id` to `account_id` with the snapshot /
          `created_at` stamps.

    Output locations (both written with `ending="parquet"`):

    - `settings.fp("installations", settings.dir_extracted, ...)`
    - `settings.fp("link_installation_account", settings.dir_extracted, ...)`
    """

    name = "extract_installations"

    _INSTALLATION_COLUMNS: list[str] = [
        "installation_id",
        "ets_id",
        "account_id",
        "registry_id",
        "registry_name",
        "installation_name",
        "eper_identification",
        "activity_type_code",
        "activity_type",
        "permit_identifier",
        "permit_revocation_date",
        "city",
        "postal_code",
        "address1",
        "address2",
        "year_of_first_emissions",
        "year_of_last_emissions",
        "snapshot_date",
    ]

    def load(self) -> None:
        self.df_raw = pd.read_csv(
            self.settings.fp("installations", self.settings.dir_source)
        )

    def transform(self) -> None:
        df = (
            self.df_raw.pipe(self._strip_str)
            .pipe(self._clean_and_create_ids)
            .pipe(self._rename_and_check)
            .assign(created_at=pd.Timestamp.now())
        )
        self.df_link = df[
            ["installation_id", "account_id", "snapshot_date", "created_at"]
        ].copy()
        self.df_installations = df.drop(columns=["account_id"])

    def save(self) -> None:
        self.df_installations.to_parquet(
            self.settings.fp(
                "installations", self.settings.dir_extracted, ending="parquet"
            ),
            index=False,
        )
        self.df_link.to_parquet(
            self.settings.fp(
                "link_installation_account",
                self.settings.dir_extracted,
                ending="parquet",
            ),
            index=False,
        )

    @staticmethod
    def _strip_str(df: pd.DataFrame) -> pd.DataFrame:
        """Strip whitespace from string columns.

        Args:
            df: Input DataFrame.

        Returns:
            DataFrame with whitespace stripped from every string column.
        """
        df = df.copy()
        str_cols = df.select_dtypes(include=["object", "string"]).columns
        df[str_cols] = df[str_cols].apply(lambda x: x.str.strip())
        return df

    @staticmethod
    def _clean_and_create_ids(df: pd.DataFrame) -> pd.DataFrame:
        """Create installation / account IDs and normalise dtypes.

        Args:
            df: DataFrame containing raw installation data (already
                whitespace-stripped).

        Returns:
            DataFrame with composite `installation_id` and `account_id`
            columns, `ets_id`, and a parsed `snapshot_date`.
        """
        map_col = {"REGISTRY_CODE": "registry_id"}
        return (
            df.assign(
                installation_id=lambda df: (
                    df.REGISTRY_CODE + "_" + df.INSTALLATION_IDENTIFIER.astype(str)
                ),
                account_id=lambda df: (
                    df.ACCOUNT_REGISTRY_CODE + "_" + df.ACCOUNT_IDENTIFIER.astype(str)
                ),
                ets_id="euets",
                snapshot_date=pd.to_datetime(df.SNAPSHOT_DATE, format="%Y-%m-%d"),
            )
            .drop(columns=["INSTALLATION_IDENTIFIER", "SNAPSHOT_DATE"])
            .rename(columns=map_col)
            .rename(columns=lambda x: x.lower())
        )

    @classmethod
    def _rename_and_check(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Select published installation columns and verify ID validity.

        Args:
            df: DataFrame containing installation data after normalisation.

        Returns:
            DataFrame containing the published installation columns.

        Raises:
            ValueError: If installation IDs are not unique, or if any
                installation ID is missing.
        """
        if not df.installation_id.is_unique:
            raise ValueError("Installation IDs are not unique.")
        if df.installation_id.isnull().any():
            raise ValueError("Some installation IDs are missing.")
        return df[cls._INSTALLATION_COLUMNS].copy()


class InstallationsBundle(Bundle):
    """Installations entity end-to-end: fetch + extract installations + link table.

    Data flow:

    - **FetchInstallationsPipeline**
        - Input: remote gzipped CSV from the EUTL public Azure blob.
        - Output: `dir_source/eutl_installations.csv` (gzip decompressed
          in-flight; written as plain CSV).
    - **ExtractInstallationsPipeline**
        - Input: `dir_source/eutl_installations.csv`.
        - Outputs:
            - `dir_extracted/eutl_installations.parquet` (cleaned
              installations table).
            - `dir_extracted/eutl_link_installation_account.parquet`
              (link table mapping `installation_id` to `account_id`).

    Run this bundle on its own to produce the published installations
    table and the installation-account link table without touching any
    other EUTL entity.
    """

    name = "eutl_installations"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            FetchInstallationsPipeline(self.settings),
            ExtractInstallationsPipeline(self.settings),
        ]
