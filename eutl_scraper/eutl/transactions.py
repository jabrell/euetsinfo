"""Transactions data flow.

Three classes covering the transactions entity end-to-end:

- :class:`FetchTransactionsPipeline` — downloads the ZIP archive from the
  European Commission, opens it in memory, and persists the inner
  transactions CSV to ``dir_source``.
- :class:`ExtractTransactionsPipeline` — reads the raw transactions CSV from
  ``dir_source``, cleans it, and emits two outputs to ``dir_extracted``: the
  cleaned transactions table and a derived projects table (both produced in
  a single cleaning pass).
- :class:`TransactionsBundle` — flat bundle of the two pipelines above.

This module is self-contained for its helper logic — cleaning helpers live
here as static methods. Shared reference data
(``map_registryCode_inv`` for mapping registry names to country codes) is
imported from :mod:`eutl_scraper.eutl.mappings` rather than duplicated.
"""

import io
import zipfile

import pandas as pd

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import DownloadClient, Settings

from .mappings import map_registryCode_inv


class FetchTransactionsPipeline(Pipeline):
    """Download the EUTL transactions ZIP from the EC and persist the inner CSV.

    Inputs:
        Remote ZIP archive served by the European Commission's climate
        document portal. The archive contains a CSV whose filename starts
        with ``transactions_EUTL_PUBLIC_NOTESD``.

    Product:
        The raw transactions table as a single DataFrame (read from the
        ZIP-embedded CSV).

    Output location:
        ``settings.fp("transactions", settings.dir_source)`` — i.e. the
        ``eutl_transactions.csv`` file under ``dir_source``.
    """

    name = "fetch_transactions"
    URL = (
        "https://climate.ec.europa.eu/document/download/"
        "0cda99f1-16f6-41e7-b190-887cd71339a4_en"
        "?filename=transactions_eutl_2024_0.zip"
    )
    CSV_PREFIX = "transactions_EUTL_PUBLIC_NOTESD"

    def __init__(self, settings: Settings, client: DownloadClient | None = None):
        """Initialise the pipeline.

        Args:
            settings (Settings): Configuration object used to resolve the
                output path via ``settings.fp("transactions", dir_source)``.
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
            self._zip_bytes: io.BytesIO = client.download_with_resume(url=self.URL)
        finally:
            if own_client:
                client.close()

    def transform(self) -> None:
        with zipfile.ZipFile(self._zip_bytes) as zf:
            csv_filename = next(
                name for name in zf.namelist() if name.startswith(self.CSV_PREFIX)
            )
            with zf.open(csv_filename) as csv_file:
                self.df = pd.read_csv(csv_file, low_memory=False)

    def save(self) -> None:
        self.df.to_csv(
            self.settings.fp("transactions", self.settings.dir_source), index=False
        )


class ExtractTransactionsPipeline(Pipeline):
    """Clean the raw transactions CSV and derive the projects table in one pass.

    Inputs:
        Raw transactions CSV produced by :class:`FetchTransactionsPipeline`,
        read from ``settings.fp("transactions", settings.dir_source)``. The
        fetch pipeline (or any equivalent that places this file on disk)
        must have run first; this pipeline does no remote calls.

    Product:
        Two cohesive outputs derived from one cleaning pass:

        - The cleaned **transactions** table — one row per transaction with
          normalised IDs (account, installation, registry), typed dates and
          project IDs, and a ``created_at`` stamp.
        - The unique **projects** table — one row per project, with project
          type imposed from the unit-type description and parsed expiry date.

    Output locations:
        - ``settings.fp("transactions", settings.dir_extracted)``
        - ``settings.fp("projects", settings.dir_extracted)``
    """

    name = "extract_transactions"

    _TRANSACTION_COLUMNS: list[str] = [
        "transaction_id",
        "transaction_type",
        "transaction_date",
        "ets_id",
        "originating_registry_id",
        "acquiring_registry_id",
        "acquiring_account_id",
        "acquiring_installation_id",
        "transferring_registry_id",
        "transferring_account_id",
        "transferring_installation_id",
        "unit_type_description",
        "supp_unit_type_description",
        "amount",
        "project_identifier",
    ]

    _PROJECT_COLUMNS: list[str] = [
        "originating_registry_id",
        "amount",
        "project_identifier",
        "lulucf_code_description",
        "unit_type_description",
        "track",
        "expiry_date",
    ]

    def load(self) -> None:
        self.df_raw = pd.read_csv(
            self.settings.fp("transactions", self.settings.dir_source),
            low_memory=False,
        )

    def transform(self) -> None:
        df_clean = self.df_raw.pipe(self._strip_str).pipe(self._clean_and_create_ids)
        self.df_transactions = self._rename_and_check(df_clean).assign(
            created_at=pd.Timestamp.now()
        )
        self.df_projects = self._create_projects(df_clean).assign(
            created_at=pd.Timestamp.now()
        )

    def save(self) -> None:
        self.df_transactions.to_csv(
            self.settings.fp("transactions", self.settings.dir_extracted),
            index=False,
        )
        self.df_projects.to_csv(
            self.settings.fp("projects", self.settings.dir_extracted),
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
        """Map registry names to codes and create account / installation IDs.

        Args:
            df (pd.DataFrame): DataFrame containing raw transaction data
                (already whitespace-stripped).

        Returns:
            pd.DataFrame: DataFrame with normalised registry IDs and unique
                ``{prefix}_account_id`` / ``{prefix}_installation_id`` columns
                for both the acquiring and transferring sides.
        """
        col_rename = {"ORIGINATING_REGISTRY": "originating_registry_id"}
        df_trans = (
            df.assign(
                acquiring_registry_id=(
                    lambda df: df.ACQUIRING_REGISTRY_NAME.str.strip().map(
                        map_registryCode_inv
                    )
                ),
                transferring_registry_id=(
                    lambda df: df.TRANSFERRING_REGISTRY_NAME.str.strip().map(
                        map_registryCode_inv
                    )
                ),
                ets_id="euets",
            )
            .rename(columns=col_rename)
            .rename(columns=lambda x: x.lower())
        )

        for prefix in ["acquiring", "transferring"]:
            mask = df_trans[f"{prefix}_account_identifier"].notna()
            df_trans.loc[mask, f"{prefix}_account_id"] = (
                df_trans.loc[mask, f"{prefix}_registry_id"]
                + "_"
                + df_trans.loc[mask, f"{prefix}_account_identifier"]
                .astype(int)
                .astype(str)
            )
            mask = df_trans[f"{prefix}_installation_installation_identifier"].notna()
            df_trans.loc[mask, f"{prefix}_installation_id"] = (
                df_trans.loc[mask, f"{prefix}_registry_id"]
                + "_"
                + df_trans.loc[mask, f"{prefix}_installation_installation_identifier"]
                .astype(int)
                .astype(str)
            )
        return df_trans

    @classmethod
    def _rename_and_check(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Select published transaction columns and retype dates / project IDs.

        Args:
            df (pd.DataFrame): DataFrame containing the transactions data
                after normalisation.

        Returns:
            pd.DataFrame: DataFrame containing the published transactions
                shape.
        """
        return df[cls._TRANSACTION_COLUMNS].assign(
            transaction_date=lambda df: pd.to_datetime(df.transaction_date),
            project_identifier=lambda df: df.project_identifier.astype("Int64"),
        )

    @classmethod
    def _create_projects(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Extract the unique projects table from cleaned transaction data.

        Args:
            df (pd.DataFrame): DataFrame containing cleaned transaction data,
                including the columns later dropped from the published
                transactions shape.

        Returns:
            pd.DataFrame: DataFrame containing one row per project, with
                project type imposed from the unit-type description and
                parsed expiry date.
        """

        def impose_project_type(unit_type_desc: str) -> str | None:
            if "RMU" in unit_type_desc:
                return "RMU"
            if "CER" in unit_type_desc:
                return "CER"
            if "tCER" in unit_type_desc:
                return "tCER"
            if "ERU" in unit_type_desc:
                return "ERU"
            return None

        return (
            df[cls._PROJECT_COLUMNS]
            .dropna(subset=["project_identifier"])
            .drop_duplicates(subset=["project_identifier"])
            .assign(
                project_type=lambda df: df.unit_type_description.map(
                    impose_project_type
                ),
                project_id=lambda df: df.project_identifier.astype("int"),
                expiry_date=lambda df: pd.to_datetime(df.expiry_date),
            )
            .drop(columns=["unit_type_description"])
        )


class TransactionsBundle(Bundle):
    """Transactions entity end-to-end: fetch the ZIP and extract transactions
    + projects.

    Pipelines (in execution order):
        1. :class:`FetchTransactionsPipeline` — downloads the ZIP, unzips, and
           writes the raw transactions CSV to ``dir_source``.
        2. :class:`ExtractTransactionsPipeline` — cleans the raw CSV and writes
           both the published transactions table and the derived projects
           table to ``dir_extracted``.

    Run this bundle on its own to produce the published transactions and
    projects tables without touching any other EUTL entity.
    """

    name = "eutl_transactions"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            FetchTransactionsPipeline(self.settings),
            ExtractTransactionsPipeline(self.settings),
        ]
