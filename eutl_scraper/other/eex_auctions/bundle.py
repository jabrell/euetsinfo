"""EEX EUA primary-auction prices end-to-end as Pipelines and a Bundle.

Orchestrates the existing sibling modules in this package:

- :mod:`.download` — scrape EEX, locate URLs, stream files to disk.
- :mod:`.extraction` — read XLSX / ZIP artefacts off disk.
- :mod:`.parsing` — clean, harmonise, type-cast.

Three classes:

- :class:`FetchEEXAuctionsPipeline` — remote → ``dir_source`` (XLSX and
  optionally the multi-year history ZIP).
- :class:`ExtractEEXAuctionsPipeline` — ``dir_source`` (XLSX, optionally
  ZIP) → ``dir_extracted`` (parquet).
- :class:`EEXAuctionsBundle` — flat bundle of the two above, with one
  source-level knob, ``download_history``.
"""

import pandas as pd

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import Settings

from .download import EEX_URL, download_file, find_first_xlsx_and_zip
from .extraction import extract_data
from .parsing import parse_auctions


class FetchEEXAuctionsPipeline(Pipeline):
    """Scrape EEX and download today's XLSX (and optionally the history ZIP).

    Inputs:
        The EEX market-data HTML page at ``EEX_URL`` plus the XLSX
        (always) and ZIP (when ``download_history=True``) it links to.

    Product:
        The raw EEX artefact(s) on disk, untouched. The current-year XLSX
        is always produced; the multi-year ZIP only when
        ``download_history`` is ``True``. Transform is identity.

    Output locations:
        - ``settings.fp("eex_auctions", settings.dir_source, ending="xlsx")``
        - ``settings.fp("eex_auctions", settings.dir_source, ending="zip")``
          (only when ``download_history=True``)

    Failure modes:
        - No XLSX link on the page → ``FileNotFoundError`` (raised by
          ``find_first_xlsx_and_zip`` in load).
        - ``download_history=True`` but no ZIP link on the page →
          ``FileNotFoundError`` (raised in save).
    """

    name = "fetch_eex_auctions"

    def __init__(self, settings: Settings, download_history: bool = False):
        super().__init__(settings)
        self.download_history = download_history

    def load(self) -> None:
        self.xlsx_url, self.zip_url = find_first_xlsx_and_zip(EEX_URL)

    def transform(self) -> None:
        # identity — raw downloads are the product of a Fetch Pipeline
        pass

    def save(self) -> None:
        xlsx_path = self.settings.fp(
            "eex_auctions", self.settings.dir_source, ending="xlsx"
        )
        download_file(self.xlsx_url, xlsx_path)
        if self.download_history:
            if self.zip_url is None:
                raise FileNotFoundError(
                    f"download_history=True but no ZIP link found on {EEX_URL}"
                )
            zip_path = self.settings.fp(
                "eex_auctions", self.settings.dir_source, ending="zip"
            )
            download_file(self.zip_url, zip_path)


class ExtractEEXAuctionsPipeline(Pipeline):
    """Read the EEX XLSX (and ZIP if present), parse, and write a parquet.

    Inputs:
        - ``settings.fp("eex_auctions", settings.dir_source, ending="xlsx")``
          — required, must exist on disk.
        - ``settings.fp("eex_auctions", settings.dir_source, ending="zip")``
          — optional, concatenated with the XLSX if present.

    Product:
        The cleaned auction-price table: harmonised column names, exploded
        country-level revenue breakdown, consistent dtypes, plus a
        ``created_at`` stamp.

    Output location:
        ``settings.fp("eex_auctions", settings.dir_extracted, ending="parquet")``

    Failure mode:
        Raises ``ValueError`` if no artefact (neither XLSX nor ZIP) is
        present on disk to extract from.
    """

    name = "extract_eex_auctions"

    def load(self) -> None:
        xlsx = self.settings.fp("eex_auctions", self.settings.dir_source, ending="xlsx")
        zip_ = self.settings.fp("eex_auctions", self.settings.dir_source, ending="zip")
        self.df_xlsx = extract_data(xlsx) if xlsx.exists() else None
        self.df_zip = extract_data(zip_) if zip_.exists() else None

    def transform(self) -> None:
        frames = [df for df in (self.df_xlsx, self.df_zip) if df is not None]
        if not frames:
            raise ValueError("No EEX auction artefact on disk to extract from.")
        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        self.df = parse_auctions(df).assign(created_at=pd.Timestamp.now())

    def save(self) -> None:
        self.df.to_parquet(
            self.settings.fp(
                "eex_auctions", self.settings.dir_extracted, ending="parquet"
            ),
            index=False,
        )


class EEXAuctionsBundle(Bundle):
    """EEX EUA primary-auction prices end-to-end: scrape + extract + parse.

    Source-level runtime config:
        ``download_history`` — whether the Fetch pipeline also pulls the
        multi-year historical ZIP. When ``True`` and the ZIP ends up on
        disk, :class:`ExtractEEXAuctionsPipeline` concatenates it with the
        current-year XLSX.
    """

    name = "eex_auctions"

    def __init__(self, settings: Settings, download_history: bool = False):
        self.download_history = download_history
        super().__init__(settings)

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            FetchEEXAuctionsPipeline(
                self.settings, download_history=self.download_history
            ),
            ExtractEEXAuctionsPipeline(self.settings),
        ]
