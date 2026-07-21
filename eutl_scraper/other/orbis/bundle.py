from pathlib import Path

import pandas as pd
from loguru import logger

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import Settings

SOURCE_DIR = Path(__file__).resolve().parent / "source"


def _load_dg_grow() -> pd.DataFrame:
    """Load the Orbis matching table created by DG GROW (Cameroon and Ho):

    Returns:
        DataFrame with the Orbis matching table.
    """
    files = {
        "2024": SOURCE_DIR / "cameron_2024.xlsx",
        "2025_first": SOURCE_DIR / "cameron_2025_first_matching.xlsx",
        "2025_update": SOURCE_DIR / "cameron_2025.xlsx",
    }
    citation = "Cameron, A. & Ho, V. (2024)"
    # citation = (
    #     "Cameron, A. & Ho, V. (2024): Matching the EU Transaction Log and ORBIS: "
    #     "A Natural Language Processing approach. URL: https://single-market-economy.ec.europa.eu/single-market/chief-economist-business-intelligence-unit/analytical-work/single-market-industry-and-competitiveness/matching-eu-transaction-log-orbis-database_en"
    # )

    lst_df = []
    for year, fn in files.items():
        logger.info(f"Loading DG GROW Orbis matching table for {year} from {fn}")
        df = pd.read_excel(fn, sheet_name="Data", dtype=str).assign(
            source=citation + f" Version: {year}"
        )
        lst_df.append(df)

    df = pd.concat(lst_df, ignore_index=True)
    return df


class ExtractOrbisMatchingPipeline(Pipeline):
    """Extract the Orbis matching tables."""

    name = "extract_orbis_matching"

    def __init__(
        self,
        settings: Settings,
    ):
        super().__init__(settings)

    def load(self) -> None:
        """Load the Orbis matching tables from the DG GROW source files and the
        table with the account holders. Note that the data model does combine
        account holders based on the company registration number. Thus we associated
        the orbis id to the holder and not the account."""
        self.df_accounts = pd.read_parquet(
            self.settings.fp("accounts", self.settings.dir_extracted, ending="parquet")
        )
        self.df_holders = pd.read_parquet(
            self.settings.fp(
                "account_holders", self.settings.dir_extracted, ending="parquet"
            )
        )
        self.df_grow = _load_dg_grow()

    def transform(self) -> None:
        """Create a table with the account holder ID and the ORBIS ID"""
        matched = set(self.df_grow.eutl_national_id.unique())
        available = set(
            self.df_holders.account_holder_company_registration_number.unique()
        )
        nr_holder = len(self.df_holders.account_holder_id.unique())
        logger.info(
            f"Account holders with ORBIS ID: {len(matched & available)} "
            f"(of {nr_holder} holders)\n Number of ORBIS IDs not matched to EUTL "
            f"account holders: {len(matched - available)}"
        )
        # create the matching table
        col_holder = {
            "account_holder_id": "account_holder_id",
            "account_holder_company_registration_number": "eutl_national_id",
        }
        col_grow = {
            "orbis_bvd_id": "orbis_bvd_id",
            "eutl_national_id": "eutl_national_id",
            "rank": "rank",
            "source": "source",
        }
        df_holder = self.df_holders.rename(columns=col_holder)[
            list(col_holder.values())
        ].drop_duplicates()

        df_grow2 = self.df_grow.rename(columns=col_grow)[
            list(col_grow.values())
        ].drop_duplicates()
        self.df_orbis_match = df_holder.merge(
            df_grow2,
            on="eutl_national_id",
            how="inner",
        ).drop(columns=["eutl_national_id"])

    def save(self) -> None:
        self.df_orbis_match.to_parquet(
            self.settings.fp(
                "map_orbis", self.settings.dir_extracted, ending="parquet"
            ),
            index=False,
        )


class ExtractOrbisMatchingBundle(Bundle):
    """ORBIS matching bundle."""

    name = "map_orbis"

    def _build_pipelines(self) -> list[Pipeline]:
        return [ExtractOrbisMatchingPipeline(self.settings)]
