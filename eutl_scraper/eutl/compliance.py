"""Compliance data flow.

Three classes covering the compliance entity end-to-end:

- `FetchCompliancePipeline` — downloads the raw compliance CSV from the
  EUTL public Azure blob and writes it to `dir_source`.
- `ExtractCompliancePipeline` — reads the raw CSV from `dir_source`,
  cleans and normalises it, and writes the result to `dir_extracted` as
  parquet.
- `ComplianceBundle` — flat bundle of the two pipelines above.
"""

import pandas as pd

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import DownloadClient, Settings


class FetchCompliancePipeline(Pipeline):
    """Download the raw EUTL compliance CSV from the EUTL public Azure blob.

    Inputs:
        Remote URL — the EUTL operators-yearly-activity daily snapshot,
        served as a gzipped CSV from the EU's public Azure blob storage.

    Output:
        The raw compliance table as a single DataFrame (gzip already
        decompressed in-flight by `DownloadClient.download_csv`).

    Output location:
        `settings.fp("compliance", settings.dir_source)` — i.e. the
        `eutl_compliance.csv` file under `dir_source`.
    """

    name = "fetch_compliance"
    URL = (
        "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/"
        "extracts/_all_extracts/operators_yearly_activity/"
        "operators_yearly_activity_daily.csv.gz"
    )

    def __init__(self, settings: Settings, client: DownloadClient | None = None):
        """Initialise the pipeline.

        Args:
            settings: Configuration object used to resolve the output path
                via `settings.fp("compliance", dir_source)`.
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
        # identity: the raw CSV is the output of a fetch pipeline
        pass

    def save(self) -> None:
        self.df.to_csv(
            self.settings.fp("compliance", self.settings.dir_source), index=False
        )


class ExtractCompliancePipeline(Pipeline):
    """Clean and normalise the raw EUTL compliance CSV into the published shape.

    Inputs:
        Raw compliance CSV produced by `FetchCompliancePipeline`, read
        from `settings.fp("compliance", settings.dir_source)`. The fetch
        pipeline (or any equivalent that places this file on disk) must
        have run first; this pipeline does no remote calls.

    Output:
        The cleaned compliance table — one row per
        `(installation_id, year)` with normalised column names, typed
        numeric fields, NA-substituted sentinels, and added
        `allocated_total` / `created_at` columns.

    Output location:
        `settings.fp("compliance", settings.dir_extracted, ending="parquet")`
        — i.e. the `eutl_compliance.parquet` file under `dir_extracted`.
    """

    name = "extract_compliance"

    _COLUMN_MAP: dict[str, str] = {
        "installation_id": "installation_id",
        "installation_name": "installation_name",
        "registry_id": "registry_id",
        "registry_name": "registry_name",
        "year": "year",
        # allocations
        "allocation": "allocated",
        "ch_allocation": "allocated_ch",
        "allocation_res": "allocation_res",
        "allocation_tra": "allocation_tra",
        # verified emissions
        "verified_emissions": "verified",
        "ch_verified_emissions": "verified_ch",
        # surrendering
        "surr_all": "surrendered",
        "surr_eua": "surrendered_eua",
        "surr_euaa": "surrendered_euaa",
        "surr_chu": "surrendered_chu",
        "surr_chua": "surrendered_chua",
        "surr_eru_from_aau": "surrendered_eru_from_aau",
        "surr_former_eua": "surrendered_former_eua",
        "surr_cer": "surrendered_cer",
        # excluded flags
        "excluded": "excluded",
        "ch_excluded": "ch_excluded",
        # snapshot date
        "snapshot_date": "snapshot_date",
    }

    def load(self) -> None:
        self.df = pd.read_csv(self.settings.fp("compliance", self.settings.dir_source))

    def transform(self) -> None:
        self.df = (
            self.df.pipe(self._strip_str)
            .pipe(self._clean_and_create_ids)
            .pipe(self._rename_and_check)
            .assign(created_at=pd.Timestamp.now())
            .pipe(self._add_total_allocations)
        )

    def save(self) -> None:
        self.df.to_parquet(
            self.settings.fp(
                "compliance", self.settings.dir_extracted, ending="parquet"
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
        """Create unique installation IDs and normalise dtypes / sentinel values.

        Args:
            df: DataFrame containing raw compliance data.

        Returns:
            DataFrame containing normalised compliance data.
        """
        map_col = {"REGISTRY_CODE": "registry_id"}
        df_c = (
            df.assign(
                installation_id=lambda df: (
                    df.REGISTRY_CODE + "_" + df.INSTALLATION_IDENTIFIER.astype(str)
                ),
                ets_id="euets",
                snapshot_date=pd.to_datetime(df.SNAPSHOT_DATE, format="%Y-%m-%d"),
            )
            .drop(columns=["INSTALLATION_IDENTIFIER", "SNAPSHOT_DATE"])
            .rename(columns=map_col)
            .rename(columns=lambda x: x.lower())
        )
        df_c = (
            df_c.replace({-1.0: pd.NA})
            .assign(
                year=lambda df: df.period_year.astype("Int64"),
                excluded=lambda df: df.excluded == "Y",
                ch_excluded=lambda df: df.ch_excluded == "Y",
            )
            .drop(columns=["period_year"])
        )
        return df_c

    @classmethod
    def _rename_and_check(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Select published columns, rename, and verify uniqueness.

        Args:
            df: DataFrame containing the compliance data after normalisation.

        Returns:
            DataFrame in the published shape.

        Raises:
            ValueError: If the compliance data is not unique by
                installation ID and year.
        """
        if not df.set_index(["installation_id", "year"]).index.is_unique:
            raise ValueError(
                "Compliance data is not unique by installation ID and year."
            )
        return df.rename(columns=cls._COLUMN_MAP)[list(cls._COLUMN_MAP.values())].copy()

    @staticmethod
    def _add_total_allocations(df: pd.DataFrame) -> pd.DataFrame:
        """Add total allocation column.

        Args:
            df: DataFrame containing compliance data.

        Returns:
            DataFrame with an added `allocated_total` column.
        """
        return df.assign(
            allocated_total=lambda df: (
                df.allocated.fillna(0)
                + df.allocation_res.fillna(0)
                + df.allocation_tra.fillna(0)
            ),
        )


class ComplianceBundle(Bundle):
    """Compliance entity end-to-end: fetch the raw CSV, then extract.

    Data flow:

    - **FetchCompliancePipeline**
        - Input: remote gzipped CSV from the EUTL public Azure blob.
        - Output: `dir_source/eutl_compliance.csv` (gzip decompressed
          in-flight; written as plain CSV).
    - **ExtractCompliancePipeline**
        - Input: `dir_source/eutl_compliance.csv`.
        - Output: `dir_extracted/eutl_compliance.parquet` (cleaned
          compliance table).

    Run this bundle on its own to produce the published compliance table
    without touching any other EUTL entity.
    """

    name = "eutl_compliance"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            FetchCompliancePipeline(self.settings),
            ExtractCompliancePipeline(self.settings),
        ]
