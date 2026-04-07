from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

SCHEMA_PATH = Path(__file__).parent / "schemas"


@dataclass
class ResourceMetadata:
    """Base class for table metadata configurations."""

    title: str
    description: str
    sources: list[dict[str, str]]
    encoding: str = "utf-8"


@dataclass
class BaseConfig:
    """Base class for table configurations with common type conversion utilities."""

    name: str
    schema_path: Path
    column_mapping: dict[str, str]
    type_convertors: dict[str, Callable]
    resource_metadata: ResourceMetadata

    @staticmethod
    def _to_datetime(col: str) -> Callable:
        """Return a function that converts a column to datetime format."""
        return lambda df: pd.to_datetime(df[col], utc=True)

    @staticmethod
    def _to_nullable_int(col: str) -> Callable:
        """Return a function that converts a column to nullable integer format."""
        return lambda df: df[col].astype("Int64")


@dataclass
class InstallationsConfig(BaseConfig):
    name: str = "installations"
    schema_path: Path = SCHEMA_PATH / "installations.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Installations",
            description=(
                "Information about the installations that are part of the European"
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
            "installation_id": "id",
            "installation_name": "name",
            "account_id": "account_id",
            "permit_identifier": "permitID",
            "eper_identification": "eperID",
            "ets_id": "ets_id",
            "registry_id": "registry_id",
            "registry_name": "registry_name",
            "activity_type_code": "activity_id",
            "activity_type": "activity_name",
            "permit_revocation_date": "permit_revocation_date",
            "city": "city",
            "postal_code": "postalCode",
            "address1": "addressMain",
            "address2": "addressSecondary",
            "year_of_first_emissions": "year_of_first_emissions",
            "year_of_last_emissions": "year_of_last_emissions",
            "snapshot_date": "snapshot_date",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "snapshot_date": self._to_datetime("snapshot_date"),
            "permit_revocation_date": self._to_datetime("permit_revocation_date"),
            "year_of_last_emissions": self._to_nullable_int("year_of_last_emissions"),
        }


@dataclass
class AccountsConfig(BaseConfig):
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
            "holder_id": "holder_id",
            "openingDate": "openingDate",
            "closingDate": "closingDate",
            "isClosurePending": "isClosurePending",
            "snapshotDate": "snapshotDate",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "openingDate": self._to_datetime("openingDate"),
            "closingDate": self._to_datetime("closingDate"),
            "snapshotDate": self._to_datetime("snapshotDate"),
        }


@dataclass
class HoldersConfig(BaseConfig):
    name: str = "holders"
    schema_path: Path = SCHEMA_PATH / "holders.yaml"
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
            "holder_id": "id",
            "accountHolderName": "name",
            "companyRegistrationNumber": "companyRegistrationNumber",
            "legalEntityIdentifier": "legalEntityIdentifier",
            "addressMain": "addressMain",
            "addressSecondary": "addressSecondary",
            "postalCode": "postalCode",
            "city": "city",
            "country": "country",
            "telephone1": "telephone1",
            "telephone2": "telephone2",
            "email": "email",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)


@dataclass
class ComplianceConfig(BaseConfig):
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
            "allocated": "allocated",
            "allocated_ch": "allocated_ch",
            "allocation_res": "allocation_res",
            "allocation_tra": "allocation_tra",
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
            "ch_excluded": "ch_excluded",
            "snapshot_date": "snapshot_date",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "snapshot_date": self._to_datetime("snapshot_date"),
        }


@dataclass
class ProjectsConfig(BaseConfig):
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
            "project_identifier": "project_identifier",
            "project_type": "project_type",
            "originating_registry_id": "originating_registry_id",
            # amount is unclear seems to be error from extration from transactions
            # table, not included in schema for now
            # "amount": "amount",
            "lulucf_code_description": "lulucf_code_description",
            "track": "track",
            "expiry_date": "expiry_date",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "expiry_date": self._to_datetime("expiry_date"),
        }


@dataclass
class TransactionsConfig(BaseConfig):
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
            "amount": "amount",
        }
    )
    type_convertors: dict[str, Callable] = field(default_factory=dict)

    def __post_init__(self):
        self.type_convertors = {
            "transaction_date": self._to_datetime("transaction_date"),
        }
