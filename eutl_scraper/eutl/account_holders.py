"""Account holders data flow.

Two classes covering the account-holders entity end-to-end:

- `ExtractAccountHoldersPipeline` — reads the PowerBI accounts Excel from
  `dir_source` (placed there by `FetchManualAccountsPipeline` in
  `AccountsBundle`), derives unique account holders and the
  account-to-holder link table, and writes both to `dir_extracted` as
  parquet.
- `AccountHoldersBundle` — flat bundle of the single pipeline above.

There is no fetch pipeline here: the manual Excel arrives in `dir_source`
via the accounts data flow. Running `AccountHoldersBundle` standalone
requires the Excel to already be staged at the expected location.

This module is self-contained for its helper logic — hashing and ID
generation live here as static methods. Shared reference data
(`map_registryCodes` for mapping country codes to registry names) is
imported from `eutl_scraper.eutl.mappings` rather than duplicated.
"""

import hashlib
import re

import pandas as pd

from eutl_scraper.pipeline import Bundle, Pipeline

from .mappings import map_registryCodes


class ExtractAccountHoldersPipeline(Pipeline):
    """Extract account holders and the link table from the manual Excel.

    Inputs:
        The PowerBI accounts Excel at
        `settings.fp("manual_accounts", settings.dir_source, ending="xlsx")`.
        That file is placed there by `FetchManualAccountsPipeline`
        (in `AccountsBundle`) — this pipeline does no fetch and does not
        read from any user-supplied path directly.

    Product:
        Two cohesive outputs derived from one cleaning pass:

        - The **account_holders** table — one row per unique account
          holder with stable hash-based `account_holder_id`, identifying
          info (name, CRN, address, city, LEI), `registry_name`, and
          `created_at`.
        - The **link_account_holder** table mapping `account_id` to
          `account_holder_id` with `created_at`.

    Output locations (both written with `ending="parquet"`):

    - `settings.fp("account_holders", settings.dir_extracted, ...)`
    - `settings.fp("link_account_holder", settings.dir_extracted, ...)`
    """

    name = "extract_account_holders"

    _COLUMN_MAP: dict[str, str] = {
        "Account Identifier": "account_identifier",
        "National Administrator": "national_administrator",
        "Account Type": "account_type",
        "Account Holder Name": "account_holder_name",
        "Account Name": "accountName",
        "Company Registration No": "account_holder_company_registration_number",
        "Main Address Line": "account_holder_address1",
        "City": "account_holder_city",
        "Legal Entity Identifier": "account_holder_lei",
        "..1": "registry_id",
        "account_id": "account_id",
    }
    _HASH_DIGITS: int = 10

    def load(self) -> None:
        src = self.settings.fp(
            "manual_accounts", self.settings.dir_source, ending="xlsx"
        )
        self.df_raw = pd.read_excel(
            src,
            skipfooter=2,
            engine="calamine",
            na_values=["-"],
            keep_default_na=True,
        )

    def transform(self) -> None:
        df = (
            self.df_raw.rename(columns=self._COLUMN_MAP)
            .assign(
                account_id=lambda df: df.apply(self._form_account_account_id, axis=1),
                account_holder_name=lambda df: (
                    df["account_holder_name"].fillna("unknown").str.strip()
                ),
            )[list(self._COLUMN_MAP.values())]
            .assign(
                account_holder_id=lambda df: df.apply(
                    lambda row: self._generate_account_holder_id(
                        row, digits=self._HASH_DIGITS
                    ),
                    axis=1,
                )
            )
        )

        # link table — one row per account
        self.df_link = df[["account_id", "account_holder_id"]].assign(
            created_at=pd.Timestamp.now()
        )
        if not self.df_link.account_id.is_unique:
            raise ValueError("account_id is not unique in link table")

        # holders table — one row per unique holder, enriched with registry_name
        self.df_holders = (
            df.drop(columns=["account_id", "accountName"])
            .drop_duplicates(subset=["account_holder_id"])
            .assign(
                created_at=pd.Timestamp.now(),
                registry_name=lambda df: df.registry_id.map(map_registryCodes),
            )
        )

    def save(self) -> None:
        self.df_link.to_parquet(
            self.settings.fp(
                "link_account_holder",
                self.settings.dir_extracted,
                ending="parquet",
            ),
            index=False,
        )
        self.df_holders.to_parquet(
            self.settings.fp(
                "account_holders", self.settings.dir_extracted, ending="parquet"
            ),
            index=False,
        )

    @staticmethod
    def _form_account_account_id(row: pd.Series) -> str | None:
        """Form `account_id` from `registry_id` and `account_identifier`.

        Args:
            row: Row of the DataFrame with `registry_id` and
                `account_identifier`.

        Returns:
            The composite `account_id`, or the (NaN) account identifier
            itself if it is missing.
        """
        if pd.isnull(row["account_identifier"]):
            return row["account_identifier"]
        return f"{row['registry_id']}_{int(row['account_identifier'])}"

    @staticmethod
    def _generate_account_holder_id(row: pd.Series, digits: int = 10) -> str:
        """Generate a stable hash-based unique identifier for the account holder.

        Args:
            row: A row from the holders DataFrame.
            digits: Number of leading hex digits to use from the SHA256
                hash. Defaults to `10`.

        Returns:
            A stable hash-based unique identifier for the account holder.
        """
        name = str(row["account_holder_name"]).strip().lower()
        raw_crn = str(row["account_holder_company_registration_number"]).strip().lower()
        is_missing = (
            pd.isnull(raw_crn)
            or raw_crn in ["", "nan", "none", "null"]
            or re.match(r"^0+$", raw_crn)
            or re.match(r"^-+$", raw_crn)
        )
        crn = "no_crn" if is_missing else raw_crn
        composite_id = f"{name}|{crn}"
        return hashlib.sha256(composite_id.encode()).hexdigest()[:digits]


class AccountHoldersBundle(Bundle):
    """Account-holders entity: extract holders and link table from the manual Excel.

    Data flow:

    - **ExtractAccountHoldersPipeline**
        - Input: `dir_source/eutl_manual_accounts.xlsx` (the PowerBI
          Excel, placed there by `FetchManualAccountsPipeline` in
          `AccountsBundle`, or by any prior step that staged the file at
          this location).
        - Outputs:
            - `dir_extracted/eutl_link_account_holder.parquet` (mapping
              `account_id` ↔ `account_holder_id`).
            - `dir_extracted/eutl_account_holders.parquet` (deduplicated
              holders with `registry_name` and `created_at`).

    Prerequisite: the manual Excel must already be in `dir_source` before
    this bundle runs. Run `AccountsBundle` first (or include both bundles
    in `EUTLBundle`) to stage it; otherwise `load` fails loud with
    `FileNotFoundError`.
    """

    name = "eutl_account_holders"

    def _build_pipelines(self) -> list[Pipeline]:
        return [ExtractAccountHoldersPipeline(self.settings)]
