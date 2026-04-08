"""The publish module contains functions to publish the data extracted and
processed by the scraper."""

import warnings

from eutl_scraper.publish.configs import (
    AccountsConfig,
    ComplianceConfig,
    HoldersConfig,
    InstallationsConfig,
    ProjectsConfig,
    TransactionsConfig,
)
from eutl_scraper.publish.configs_additional_data import (
    EEXAuctions,
    InstallationLocations,
    NaceMappings,
)

from .prepare_tables import prepare_table
from .resources import create_data_package, create_resource

# Ignore warnings about incompatible versions of urllib3 and chardet, which are
# dependencies of frictionless. This is a known issue of requests and can be safely
# ignored.
warnings.filterwarnings(
    "ignore", message="urllib3.*or chardet.*doesn't match a supported version"
)

__all__ = ["TABLE_REGISTRY", "prepare_table", "create_resource", "create_data_package"]


TABLE_REGISTRY = {
    "installations": InstallationsConfig(),
    "accounts": AccountsConfig(),
    "holders": HoldersConfig(),
    "compliance": ComplianceConfig(),
    "projects": ProjectsConfig(),
    "transactions": TransactionsConfig(),
    "installation_locations": InstallationLocations(),
    "nace_mappings": NaceMappings(),
    "eex_auctions": EEXAuctions(),
}
