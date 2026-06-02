"""Bundle abstraction.

A `Bundle` is a named, **flat** list of `Pipeline` instances. The list is
the bundle's content; running the bundle runs the pipelines in order. A
Bundle never contains another Bundle — bundles compose by *flattening*: a
coarser bundle's `_build_pipelines` inlines a finer bundle's `.pipelines`
attribute at construction time. This keeps the runtime model simple (a
bundle is always a list of pipelines, never a tree) while still allowing
the user to run a finer-grained bundle on its own.

A Bundle is not a Pipeline. Its only runtime behaviour is `run`, which
iterates the pipeline list in declared order. There is no dependency
resolution and no topological sort.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from loguru import logger

from ..settings import Settings
from .pipeline import Pipeline


class Bundle(ABC):
    """Abstract base for a named, flat list of pipelines.

    Subclasses declare `name` at class level and implement
    `_build_pipelines`, which returns the pipelines in the order they
    should run. Subclass `__init__` may take additional runtime config
    (API keys, user-supplied file paths, knobs); it should store any such
    config on `self` and then call `super().__init__(settings)`.

    A bundle can be composed of finer bundles by flattening their
    `.pipelines` attribute in `_build_pipelines`. Composition lives at the
    factory level, not in the runtime type — the bundle still holds a
    flat `list[Pipeline]`.

    Example — a per-entity bundle holding two pipelines:

    ```python
    class ComplianceBundle(Bundle):
        '''Compliance entity: fetch the raw CSV, then extract the cleaned table.'''

        name = "eutl_compliance"

        def _build_pipelines(self):
            return [
                FetchCompliancePipeline(self.settings),
                ExtractCompliancePipeline(self.settings),
            ]
    ```

    Example — a coarser bundle composing several finer bundles:

    ```python
    class EUTLBundle(Bundle):
        '''Full EUTL data flow, composed from per-entity bundles.'''

        name = "eutl"

        def _build_pipelines(self):
            return [
                *ComplianceBundle(self.settings).pipelines,
                # ...further per-entity bundles and cross-entity augments...
            ]
    ```
    """

    name: ClassVar[str]

    def __init__(self, settings: Settings):
        """Initialise the bundle and build its pipeline list.

        Args:
            settings: Configuration object passed through to each pipeline
                constructed by `_build_pipelines`.
        """
        self.settings = settings
        self.pipelines: list[Pipeline] = self._build_pipelines()

    @abstractmethod
    def _build_pipelines(self) -> list[Pipeline]:
        """Return the bundle's pipelines in execution order.

        Subclasses use `self.settings` (and any subclass-specific config
        stored on `self` before `super().__init__`) to construct the list.
        Conditional inclusion (e.g. only add a pipeline when its API key
        is provided) belongs here, not in `run`. To compose from finer
        bundles, splat their `.pipelines` into the returned list.
        """

    def run(self) -> None:
        """Run the bundle's pipelines in declared order."""
        for p in self.pipelines:
            logger.info(f"[{self.name}] running {p.name}")
            p.run()
