"""Bundle abstraction.

A :class:`Bundle` is a named, source-level grouping of :class:`Pipeline`
instances. Each source — EUTL, EEX, NACE, Geocoding — has its own concrete
``Bundle`` subclass that:

- declares a :attr:`name`,
- accepts source-level runtime config (API keys, manually-downloaded file
  paths, knobs) via its ``__init__``,
- builds its pipeline list in :meth:`_build_pipelines`.

A Bundle is not a Pipeline. Its only runtime behaviour is :meth:`run`, which
iterates the pipeline list in declared order. There is no dependency
resolution and no topological sort.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from loguru import logger

from ..settings import Settings
from .pipeline import Pipeline


class Bundle(ABC):
    """Abstract base for a source-level grouping of pipelines.

    Subclasses declare :attr:`name` at class level and implement
    :meth:`_build_pipelines`. Subclass ``__init__`` should store any extra
    runtime config on ``self`` (so :meth:`_build_pipelines` can read it) and
    then call ``super().__init__(settings)``.

    Example::

        class GeocodingBundle(Bundle):
            name = "geocoding"

            def __init__(self, settings, api_keys, max_installations=None):
                self.api_keys = api_keys
                self.max_installations = max_installations
                super().__init__(settings)

            def _build_pipelines(self):
                pipelines = []
                if "geoapify" in self.api_keys:
                    pipelines.append(
                        GeoapifyGeocodingPipeline(
                            self.settings,
                            key=self.api_keys["geoapify"],
                            max_installations=self.max_installations,
                        )
                    )
                return pipelines
    """

    name: ClassVar[str]

    def __init__(self, settings: Settings):
        """Initialise the bundle and build its pipeline list.

        Args:
            settings (Settings): Configuration object passed through to each
                pipeline constructed by :meth:`_build_pipelines`.
        """
        self.settings = settings
        self.pipelines: list[Pipeline] = self._build_pipelines()

    @abstractmethod
    def _build_pipelines(self) -> list[Pipeline]:
        """Return the bundle's pipelines in execution order.

        Subclasses use ``self.settings`` (and any subclass-specific config
        stored on ``self`` before ``super().__init__``) to construct the list.
        Conditional inclusion (e.g. only add the Geoapify pipeline when its
        API key is provided) belongs here, not in :meth:`run`.
        """

    def run(self) -> None:
        """Run the bundle's pipelines in declared order."""
        for p in self.pipelines:
            logger.info(f"[{self.name}] running {p.name}")
            p.run()
