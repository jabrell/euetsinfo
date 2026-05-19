"""EUTL bundle.

Source-level grouping of all EUTL pipelines (fetch, extract, augment). Today
this bundle contains only the compliance pipelines; further entities
(accounts, installations, transactions, account holders) will be added as
they are migrated.
"""

from eutl_scraper.pipeline import Bundle, Pipeline

from .compliance import ExtractCompliancePipeline, FetchCompliancePipeline


class EUTLBundle(Bundle):
    """Bundle of all pipelines processing data from the EUTL public source.

    The EUTL (European Union Transaction Log) is the EU's official registry
    for the EU ETS. This bundle owns the fetch / extract / augment pipelines
    for every entity sourced from it.
    """

    name = "eutl"

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            FetchCompliancePipeline(self.settings),
            ExtractCompliancePipeline(self.settings),
        ]
