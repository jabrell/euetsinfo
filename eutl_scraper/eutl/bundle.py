"""EUTL bundle.

Top-level bundle for the EUTL data source. Composed by flattening the
per-entity bundles (compliance, transactions, accounts, installations,
account holders) plus the two cross-entity augment pipelines
(`CreateETS2InstallationsPipeline`, `AddMissingAccountsFromTransactionsPipeline`).

Running this bundle runs every EUTL pipeline; running a per-entity bundle
(e.g. `ComplianceBundle`) runs only its slice.
"""

from eutl_scraper.pipeline import Bundle, Pipeline

from .account_holders import AccountHoldersBundle
from .accounts import AccountsBundle
from .add_missing_accounts_from_transactions import (
    AddMissingAccountsFromTransactionsPipeline,
)
from .compliance import ComplianceBundle
from .create_ets2_installations import CreateETS2InstallationsPipeline
from .installations import InstallationsBundle
from .transactions import TransactionsBundle


class EUTLBundle(Bundle):
    """All pipelines processing data from the EUTL public source.

    The EUTL (European Union Transaction Log) is the EU's official
    registry for the EU ETS. This bundle composes the per-entity bundles
    for every entity sourced from it, followed by the cross-entity
    augment pipelines that depend on multiple entities being on disk.

    Execution order:

    1. `ComplianceBundle` — fetch + extract compliance.
    2. `TransactionsBundle` — fetch + extract transactions + projects.
    3. `AccountsBundle` — fetch Azure CSV, copy manual Excel, extract.
    4. `InstallationsBundle` — fetch + extract installations + link table.
    5. `AccountHoldersBundle` — extract holders from the manual Excel.
    6. `CreateETS2InstallationsPipeline` — augment installations with
       ETS2 stubs inferred from compliance.
    7. `AddMissingAccountsFromTransactionsPipeline` — augment accounts
       with stubs for parties seen only in transactions.

    To run only one entity, instantiate that entity's bundle directly —
    e.g. `ComplianceBundle(settings).run()`.
    """

    name = "eutl"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            *ComplianceBundle(self.settings).pipelines,
            *TransactionsBundle(self.settings).pipelines,
            *AccountsBundle(self.settings).pipelines,
            *InstallationsBundle(self.settings).pipelines,
            *AccountHoldersBundle(self.settings).pipelines,
            CreateETS2InstallationsPipeline(self.settings),
            AddMissingAccountsFromTransactionsPipeline(self.settings),
        ]
