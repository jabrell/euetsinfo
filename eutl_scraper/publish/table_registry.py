"""Registry mapping table names to publication configuration instances.

`TABLE_REGISTRY` is the single lookup used by `publish_data_package`: it
resolves a logical table name (matching the keys in `data_paths`) to an
instantiated `BaseConfig` subclass. To publish a new table, instantiate
its config here under the appropriate name and add the corresponding
extracted-file path in `publish_data_package`.
"""

from .configs import (
    AccountHoldersConfig,
    AccountsConfig,
    ComplianceConfig,
    InstallationsConfig,
    LinkAccountHolderConfig,
    LinkInstallationAccountConfig,
    ProjectsConfig,
    TransactionsConfig,
)
from .configs_additional_data import (
    EEXAuctions,
    InstallationLocations,
    NaceMappings,
)

TABLE_REGISTRY = {
    "installations": InstallationsConfig(),
    "accounts": AccountsConfig(),
    "account_holders": AccountHoldersConfig(),
    "compliance": ComplianceConfig(),
    "projects": ProjectsConfig(),
    "transactions": TransactionsConfig(),
    "installation_locations": InstallationLocations(),
    "nace_mappings": NaceMappings(),
    "eex_auctions": EEXAuctions(),
    "link_installation_account": LinkInstallationAccountConfig(),
    "link_account_holder": LinkAccountHolderConfig(),
}
