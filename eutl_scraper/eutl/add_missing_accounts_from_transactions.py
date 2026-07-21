"""Augment accounts with stubs for parties that appear only in transactions.

One pipeline class:

- `AddMissingAccountsFromTransactionsPipeline` — reads the raw
  transactions CSV and the extracted accounts parquet, derives unique
  transaction parties, finds `account_id`s absent from the accounts
  table, and overwrites the accounts parquet with the augmented table.
"""

import pandas as pd
from loguru import logger

from eutl_scraper.eutl.mappings import map_registryCode_inv
from eutl_scraper.pipeline import Pipeline


class AddMissingAccountsFromTransactionsPipeline(Pipeline):
    """Append stub accounts for parties seen in transactions but absent from accounts.

    Inputs:

    - Raw transactions CSV at
      `settings.fp("transactions", settings.dir_source)` — uppercase
      per-side party columns (`ACQUIRING_ACCOUNT_NAME` /
      `TRANSFERRING_ACCOUNT_NAME`, `*_ACCOUNT_OPEN_DT`,
      `*_ACCOUNT_TYPE2`, holder fields, …) needed for stub detail that
      `ExtractTransactionsPipeline` does not preserve.
    - Extracted accounts parquet at
      `settings.fp("accounts", settings.dir_extracted, ending="parquet")`.

    Output:
        The accounts table with one stub row appended per missing
        `account_id`. Stubs carry `accountName` (defaulted to
        `"NotKnown"` if NA on the transaction side), `openingDate`,
        `closingDate`, `account_id`, `account_type` (last `-`-separated
        token of `account_type2`), `isClosurePending=NA`, and
        `snapshotDate` / `created_at` copied from the existing accounts
        (assumes single-valued — same assumption as legacy).

    Output location:
        `settings.fp("accounts", settings.dir_extracted, ending="parquet")`
        — overwrites the file produced by `ExtractAccountsPipeline`.

    Failure modes (raise `ValueError`):

    - Derived `account_id` not unique across constructed transaction
      parties.
    - Existing `snapshotDate` or `created_at` not single-valued in the
      accounts table.

    No-op:
        Zero missing accounts is a clean no-op — the existing accounts
        file is left untouched (no rewrite).
    """

    name = "add_missing_accounts_from_transactions"

    _PARTY_PREFIXES = ("TRANSFERRING", "ACQUIRING")
    _PARTY_COLUMN_MAP = {
        "REGISTRY_NAME": "registryName",
        "ACCOUNT_TYPE1": "account_type1",
        "ACCOUNT_TYPE2": "account_type2",
        "ACCOUNT_TYPE3": "account_type3",
        "ACCOUNT_OPEN_DT": "openingDate",
        "ACCOUNT_END_OF_VALIDITY": "closingDate",
        "ACCOUNT_NAME": "accountName",
        "ACCOUNT_IDENTIFIER": "account_identifier",
        "ACCOUNT_HOLDER": "account_holder_name",
        "ACCOUNT_HOLDER_ADDRESS1": "account_holder_address1",
        "ACCOUNT_HOLDER_ADDRESS2": "account_holder_address2",
        "ACCOUNT_HOLDER_CITY": "account_holder_city",
        "ACCOUNT_HOLDER_POSTAL_CODE": "account_holder_postal_code",
        "ACCOUNT_HOLDER_COUNTRY_CODE": "account_holder_country_code",
        "ACCOUNT_HOLDER_COMPANY_REGISTRATION_NUMBER": (
            "account_holder_company_registration_number"
        ),
        "ACCOUNT_HOLDER_LEI": "account_holder_lei",
    }
    _STUB_COLUMNS = [
        "accountName",
        "openingDate",
        "closingDate",
        "account_id",
        "account_type2",
        "registry_id",
    ]

    def load(self) -> None:
        self.df_transactions_raw = pd.read_csv(
            self.settings.fp("transactions", self.settings.dir_source),
            low_memory=False,
        )
        self.df_accounts = pd.read_parquet(
            self.settings.fp("accounts", self.settings.dir_extracted, ending="parquet")
        )

    def transform(self) -> None:
        df_parties = self._build_transaction_parties(self.df_transactions_raw)
        missing = set(df_parties.account_id) - set(self.df_accounts.account_id)
        if not missing:
            logger.info("No missing accounts — nothing to augment.")
            self.df_augmented = None
            return
        logger.warning(
            f"{len(missing)} accounts from transactions are missing from the "
            "accounts table. Adding stub rows with limited information "
            "(account type, account name, opening and closing date)."
        )
        df_missing_parties = df_parties.loc[df_parties.account_id.isin(missing)]

        snapshot = self._single_value(self.df_accounts, "snapshotDate")
        created = self._single_value(self.df_accounts, "created_at")

        df_missing = (
            df_missing_parties[self._STUB_COLUMNS]
            .assign(
                accountName=lambda df: df["accountName"].fillna("NotKnown"),
                registry_id=lambda df: df["registry_id"].str.split("_").str[0],
                account_type=lambda df: df["account_type2"].map(
                    self._format_account_type
                ),
                isClosurePending=pd.NA,
                snapshotDate=snapshot,
                created_at=created,
            )
            .drop(columns=["account_type2"])
        )
        self.df_augmented = pd.concat([self.df_accounts, df_missing], ignore_index=True)

    def save(self) -> None:
        if self.df_augmented is None:
            return
        self.df_augmented.to_parquet(
            self.settings.fp("accounts", self.settings.dir_extracted, ending="parquet"),
            index=False,
        )

    @classmethod
    def _build_transaction_parties(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Stack acquiring and transferring party blocks into one party table."""
        frames = []
        for prefix in cls._PARTY_PREFIXES:
            rename = {
                f"{prefix}_{src}": dst for src, dst in cls._PARTY_COLUMN_MAP.items()
            }
            frames.append(
                df[list(rename.keys())]
                .rename(columns=rename)
                .assign(
                    registry_id=lambda x: (
                        x["registryName"].str.strip().map(map_registryCode_inv)
                    )
                )
            )
        df_parties = (
            pd.concat(frames, ignore_index=True)
            .dropna(subset=["account_identifier"])
            .assign(
                account_identifier=lambda df: df["account_identifier"].astype("int64"),
                account_id=lambda df: df.apply(cls._form_account_id, axis=1),
            )
            .drop_duplicates()
        )
        if not df_parties.account_id.is_unique:
            raise ValueError(
                "Derived account_id is not unique across transaction parties."
            )
        return df_parties

    @staticmethod
    def _form_account_id(row: pd.Series) -> str | float:
        if pd.isnull(row["account_identifier"]):
            return row["account_identifier"]
        return f"{row['registry_id']}_{int(row['account_identifier'])}"

    @staticmethod
    def _format_account_type(x: str):
        if x == "-":
            return pd.NA
        return x.split("-")[-1]

    @staticmethod
    def _single_value(df: pd.DataFrame, col: str):
        values = df[col].dropna().unique()
        if len(values) != 1:
            raise ValueError(
                f"Expected exactly one unique non-NA value in '{col}', "
                f"got {len(values)}: {values[:5]}"
            )
        return values[0]
