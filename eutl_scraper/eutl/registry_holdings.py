"""Registry holdings data flow.

Four classes covering the registry holdings end-to-end:

- `FetchRegistryHoldingsPipeline` — downloads the raw registry holdings
    CSV from the EUTL public Azure blob and writes it to `dir_source`.
- `ExtractRegistryHoldingsPipeline` — reads the raw registry holdings CSV from
  `dir_source`, cleans and normalises it, and writes the result to
  `dir_extracted` as parquet.
- `RegistryHoldingsBundle` — flat bundle of the three pipelines above.

This module is self-contained for its helper logic — cleaning helpers
live here as static methods on `ExtractRegistryHoldingsPipeline`, not imported
from elsewhere.
"""

import pandas as pd  # noqa: F401

from eutl_scraper.pipeline import Bundle, Pipeline  # noqa: F401
from eutl_scraper.settings import DownloadClient, Settings


class FetchFetchRegistryHoldingsPipeline(Pipeline):
    """Download the daily snapshot of EUTL registry holdings from the EUTL
    public Azure blob.

    Inputs:
        Remote URL — the EUTL registry holdings daily snapshot, served as a
        gzipped CSV from the EU's public Azure blob storage.

    Output:
        The raw registry holdings table as a single DataFrame (gzip already
        decompressed in-flight by `DownloadClient.download_csv`).

    Output location:
        `settings.fp("registry_holdings", settings.dir_source)` — i.e. the
        `eutl_registry_holdings.csv` file under `dir_source`.
    """

    name = "fetch_registry_holdings"
    URL = (
        "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/"
        "_all_extracts/registry_holdings/registry_holdings_daily.csv.gz"
    )

    def __init__(self, settings: Settings, client: DownloadClient | None = None):
        """Initialise the pipeline.

        Args:
            settings: Configuration object used to resolve the output path
                via `settings.fp("accounts", dir_source)`.
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
            self.settings.fp("accounts", self.settings.dir_source), index=False
        )
