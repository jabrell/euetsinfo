"""Per-table publication configurations for core EUTL entities.

Each `*Config` dataclass declares everything the publication layer needs
for one output table: the canonical name, the path to the Frictionless
YAML schema under `schemas/`, the resource-level metadata (title,
description, upstream sources), the raw → published column renaming, and
the type converters / transformers applied before renaming.

`BaseConfig` provides the shared structure plus a handful of helper
factories (`_to_datetime`, `_to_nullable_int`, `_dropna_subset`,
`_format_nace`, `_drop_duplicates_subset`) used by the concrete configs.
`ResourceMetadata` collects the descriptive fields attached to the
Frictionless `Resource` after preparation.

The configs in this module cover the EUTL-sourced tables; auxiliary
configs (locations, NACE, EEX auctions) live in
`configs_additional_data`. Both are registered in `table_registry`.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

SCHEMA_PATH = Path(__file__).parent / "schemas"


@dataclass
class ResourceMetadata:
    """Descriptive metadata attached to a Frictionless `Resource`.

    Mirrors the subset of Frictionless resource fields the scraper sets
    when publishing a table: human-readable `title`, longer
    `description`, the list of upstream `sources`, and the text
    `encoding` of the published CSV.
    """

    title: str
    description: str
    sources: list[dict[str, str]]
    encoding: str = "utf-8"


@dataclass
class BaseConfig:
    """Shared structure for per-table publication configurations.

    Subclasses set sensible defaults for `name`, `schema_path`,
    `resource_metadata`, `column_mapping`, and (in `__post_init__`)
    `type_convertors` and `transformers`. They are consumed by
    `prepare_table` (type/transformer/rename pipeline) and
    `create_resource` (schema validation + metadata attachment).

    The static helpers return callables suitable for `type_convertors`
    (column-level) or `transformers` (DataFrame-level) so concrete
    configs stay declarative.
    """

    name: str
    schema_path: Path
    resource_metadata: ResourceMetadata
    column_mapping: dict[str, str]
    type_convertors: dict[str, Callable] = field(default_factory=dict)
    transformers: list[Callable] = field(default_factory=list)

    @staticmethod
    def _to_datetime(col: str, errors: str = "coerce") -> Callable:
        """Return a function that converts a column to datetime format."""
        return lambda df: pd.to_datetime(df[col], utc=True, errors=errors)

    @staticmethod
    def _to_nullable_int(col: str) -> Callable:
        """Return a function that converts a column to nullable integer format."""
        return lambda df: df[col].astype("Int64")

    @staticmethod
    def _dropna_subset(cols: list[str]) -> Callable:
        """Return a function that drops rows where all specified columns are NA."""
        return lambda df: df.dropna(subset=cols, how="all")

    @staticmethod
    def _format_nace(col: str, format: str = ".2f") -> Callable:
        """Format a NACE code column as a zero-padded decimal string.

        Inputs may be strings (parquet preserves the leakage-list ``str``
        dtype) or numeric; both are coerced to float before formatting so
        the published values match the previous CSV-era output.
        """

        def _convert(df: pd.DataFrame) -> pd.Series:
            numeric = pd.to_numeric(df[col], errors="coerce")
            return numeric.apply(lambda x: f"{x:{format}}" if pd.notna(x) else None)

        return _convert

    @staticmethod
    def _drop_duplicates_subset(cols: list[str]) -> Callable:
        """Return a function that drops duplicate rows based on specified columns."""
        return lambda df: df.drop_duplicates(subset=cols)


@dataclass
class InstallationsConfig(BaseConfig):
    """Publication config for the `installations` table.

    Covers the installations participating in the EU ETS. ETS2 stub rows
    created by the augment step are included; they carry `ets_id="ETS2"`
    and have no associated account.
    """

    name: str = "installations"
    schema_path: Path = SCHEMA_PATH / "installations.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Installations",
            description=(
                "Information about the installations that are part of the European"
                " Union Emissions Trading System (EU ETS)."
                " Note that for euets installations, the account_id is mandatory "
                "However, ETS2 accounts are currently derived as they appear in the "
                "compliance data. They do not relate to an account_id"
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "id",
            "installation_name": "name",
            "permit_identifier": "permitID",
            "eper_identification": "eperID",
            "ets_id": "ets_id",
            "registry_id": "registry_id",
            "registry_name": "registry_name",
            "activity_type_code": "activity_id",
            "activity_type": "activity_name",
            "permit_revocation_date": "permit_revocation_date",
            "city": "city",
            "postal_code": "postal_code",
            "address1": "address_main",
            "address2": "address_secondary",
            "year_of_first_emissions": "year_of_first_emissions",
            "year_of_last_emissions": "year_of_last_emissions",
            "snapshot_date": "snapshot_date",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "snapshot_date": self._to_datetime("snapshot_date"),
            "permit_revocation_date": self._to_datetime("permit_revocation_date"),
            "year_of_last_emissions": self._to_nullable_int("year_of_last_emissions"),
            "activity_type_code": self._to_nullable_int("activity_type_code"),
            "year_of_first_emissions": self._to_nullable_int("year_of_first_emissions"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class AccountsConfig(BaseConfig):
    """Publication config for the `accounts` table.

    Covers the registry accounts in the EU ETS. Stub rows added by the
    augment step for accounts seen only in transactions are included.
    """

    name: str = "accounts"
    schema_path: Path = SCHEMA_PATH / "accounts.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Accounts",
            description=(
                "Information about the accounts that are part of the European"
                " Union Emissions Trading System (EU ETS)."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "account_id": "id",
            "accountName": "name",
            "account_type": "account_type",
            "openingDate": "opening_date",
            "closingDate": "closing_date",
            "isClosurePending": "is_closure_pending",
            "snapshotDate": "snapshot_date",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "openingDate": self._to_datetime("openingDate", errors="coerce"),
            "closingDate": self._to_datetime("closingDate", errors="coerce"),
            "snapshotDate": self._to_datetime("snapshotDate"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class AccountHoldersConfig(BaseConfig):
    """Publication config for the `account_holders` table.

    Account holders are derived from the manually-exported PowerBI
    accounts XLSX; they are not directly available in the public EUTL
    data feed.
    """

    name: str = "account_holders"
    schema_path: Path = SCHEMA_PATH / "account_holders.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS AccountHolders",
            description=(
                "Information about the account holders that are part of the European"
                " Union Emissions Trading System (EU ETS). Account holders are the "
                "legal entities that hold accounts in the EU ETS and are responsible "
                "for the operation of the accounts. Note that account holders can hold "
                "multiple accounts. Account holders are derived from data in the "
                "accounts and transactions table and are not directly available in "
                "the EUTL database."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "account_holder_id": "id",
            "account_holder_name": "name",
            "account_holder_company_registration_number": "company_registration_number",
            "account_holder_lei": "legal_entity_identifier",
            "account_holder_address1": "address_main",
            "account_holder_city": "city",
            "registry_id": "registry_id",
            "registry_name": "registry_name",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class ComplianceConfig(BaseConfig):
    """Publication config for the `compliance` table.

    Per-installation, per-year compliance data: allocations, verified
    emissions, surrendered units (broken out by unit type), and
    exclusion flags.
    """

    name: str = "compliance"
    schema_path: Path = SCHEMA_PATH / "compliance.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Compliance",
            description=(
                "Information about the compliance status of installations "
                "that are part of the European  Union Emissions Trading System "
                "(EU ETS)."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "year": "year",
            "installation_name": "installation_name",
            "registry_id": "registry_id",
            "registry_name": "registry_name",
            "allocated_total": "allocated",
            "allocated": "allocated_free",
            "allocated_ch": "allocated_ch",
            "allocation_res": "allocated_reserve",
            "allocation_tra": "allocated_transitional",
            "verified": "verified",
            "verified_ch": "verified_ch",
            "surrendered": "surrendered",
            "surrendered_eua": "surrendered_eua",
            "surrendered_euaa": "surrendered_euaa",
            "surrendered_chu": "surrendered_chu",
            "surrendered_chua": "surrendered_chua",
            "surrendered_eru_from_aau": "surrendered_eru_from_aau",
            "surrendered_former_eua": "surrendered_former_eua",
            "surrendered_cer": "surrendered_cer",
            "excluded": "excluded",
            "ch_excluded": "excluded_ch",
            "snapshot_date": "snapshot_date",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "snapshot_date": self._to_datetime("snapshot_date"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class ProjectsConfig(BaseConfig):
    """Publication config for the `projects` table.

    CDM/JI projects that issued credits eligible for EU ETS surrender.
    Records are derived from the transactions table during extraction.
    """

    name: str = "projects"
    schema_path: Path = SCHEMA_PATH / "projects.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Projects",
            description=(
                "Information about the CDM and JI projects that created allowances "
                " in the European  Union Emissions Trading System (EU ETS). The data "
                "is derived from the transactions table"
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "project_id": "id",
            "project_type": "project_type",
            "originating_registry_id": "originating_registry_id",
            # amount is unclear seems to be error from extration from transactions
            # table, not included in schema for now
            # "amount": "amount",
            "lulucf_code_description": "lulucf_code_description",
            "track": "track",
            "expiry_date": "expiry_date",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "expiry_date": self._to_datetime("expiry_date"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class TransactionsConfig(BaseConfig):
    """Publication config for the `transactions` table.

    Unit-level transactions in the EU ETS registry — transferring and
    acquiring registries/accounts/installations, unit types, and amounts.
    """

    name: str = "transactions"
    schema_path: Path = SCHEMA_PATH / "transactions.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Transactions",
            description=(
                "Information about the transactions in the European Union Emissions "
                "Trading System (EU ETS)."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "transaction_id": "id",
            "transaction_date": "date",
            "ets_id": "ets_id",
            "transaction_type": "transaction_type",
            "originating_registry_id": "originating_registry_id",
            "acquiring_registry_id": "acquiring_registry_id",
            "acquiring_account_id": "acquiring_account_id",
            "acquiring_installation_id": "acquiring_installation_id",
            "transferring_registry_id": "transferring_registry_id",
            "transferring_account_id": "transferring_account_id",
            "transferring_installation_id": "transferring_installation_id",
            "unit_type_description": "unit_type_description",
            "supp_unit_type_description": "supp_unit_type_description",
            "project_identifier": "project_id",
            "amount": "amount",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "project_identifier": self._to_nullable_int("project_identifier"),
            "transaction_date": self._to_datetime("transaction_date"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class LinkInstallationAccountConfig(BaseConfig):
    """Publication config for the `link_installation_account` table.

    Many-to-one mapping between installations and the accounts holding
    their allowances, snapshotted at the EUTL crawl date.
    """

    name: str = "link_installation_account"
    schema_path: Path = SCHEMA_PATH / "link_installation_account.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Link Installation Account",
            description=(
                "Information about the link between installations and accounts in "
                "the European Union Emissions Trading System (EU ETS)."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "account_id": "account_id",
            "snapshot_date": "snapshot_date",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "snapshot_date": self._to_datetime("snapshot_date"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class LinkAccountHolderConfig(BaseConfig):
    """Publication config for the `link_account_holder` table.

    Many-to-one mapping between accounts and the account holders that
    operate them.
    """

    name: str = "link_account_holder"
    schema_path: Path = SCHEMA_PATH / "link_account_holder.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Link Account Holder",
            description=(
                "Information about the link between account holders and accounts in "
                "the European Union Emissions Trading System (EU ETS)."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                }
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "account_id": "account_id",
            "account_holder_id": "holder_id",
            "created_at": "created_at",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "created_at": self._to_datetime("created_at"),
        }
