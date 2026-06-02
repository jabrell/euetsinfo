from .eutl import EUTLBundle
from .other import (
    EEXAuctionsBundle,
    InstallationLocationsBundle,
    NaceFromLeakageListsBundle,
)
from .pipeline import Bundle, Pipeline
from .settings import Settings


class AllDataBundle(Bundle):
    """All pipelines processing data from the EUTL public source and related
    other sources.
    """

    name = "all_data"

    def __init__(
        self,
        settings: Settings,
        api_keys: dict[str, str],
        max_installations: int | None = None,
    ):
        self.api_keys = api_keys
        self.max_installations = max_installations
        super().__init__(settings)

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            *EUTLBundle(self.settings).pipelines,
            *EEXAuctionsBundle(self.settings).pipelines,
            *NaceFromLeakageListsBundle(self.settings).pipelines,
            *InstallationLocationsBundle(
                self.settings,
                api_keys=self.api_keys,
                max_installations=self.max_installations,
            ).pipelines,
        ]
