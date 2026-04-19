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
