"""EUTL bundle.

Top-level bundle for the EUTL data source. Composed by flattening the
per-entity bundles (compliance, and — as the migration progresses — accounts,
installations, transactions, account holders) plus any cross-entity augment
pipelines. Running this bundle runs every EUTL pipeline; running a per-entity
bundle (e.g. :class:`ComplianceBundle`) runs only its slice.
"""

from eutl_scraper.pipeline import Bundle, Pipeline

from .account_holders import AccountHoldersBundle
from .accounts import AccountsBundle
from .compliance import ComplianceBundle
from .installations import InstallationsBundle
from .transactions import TransactionsBundle


class EUTLBundle(Bundle):
    """All pipelines processing data from the EUTL public source.

    The EUTL (European Union Transaction Log) is the EU's official registry
    for the EU ETS. This bundle composes the per-entity bundles for every
    entity sourced from it. Today only :class:`ComplianceBundle` is included;
    further entity bundles and cross-entity augment pipelines will be added
    as they are migrated.

    To run only one entity, instantiate that entity's bundle directly — e.g.
    ``ComplianceBundle(settings).run()``.
    """

    name = "eutl"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            *ComplianceBundle(self.settings).pipelines,
            *TransactionsBundle(self.settings).pipelines,
            *AccountsBundle(self.settings).pipelines,
            *InstallationsBundle(self.settings).pipelines,
            *AccountHoldersBundle(self.settings).pipelines,
        ]
