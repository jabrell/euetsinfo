"""Pipeline abstraction.

A `Pipeline` is a unit of data processing with three fixed phases
executed in order by `Pipeline.run`:

1. `load` — bring inputs into memory (remote fetch and/or local read).
2. `transform` — turn inputs into the pipeline's output.
3. `save` — persist the output to disk.

Every pipeline produces exactly one cohesive output (which may span
multiple files). The three phases are abstract; `run` is concrete and
enforces the order, so subclasses cannot skip or reorder phases.
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from loguru import logger

from ..settings import Settings


class Pipeline(ABC):
    """Abstract base for a single load → transform → save unit.

    Concrete subclasses declare `name` as a class-level attribute and
    implement `load`, `transform`, and `save`. `run` is concrete and
    always invokes the three phases in order.

    Subclasses may extend `__init__` to accept pipeline-specific runtime
    config (e.g. an API key, a user-supplied file path); they should call
    `super().__init__(settings)`. Intermediate state between phases lives
    as instance attributes on the subclass and is not prescribed by this
    base.
    """

    name: ClassVar[str]

    def __init__(self, settings: Settings):
        """Initialise the pipeline.

        Args:
            settings: Configuration object used to resolve disk paths via
                `settings.fp(...)`.
        """
        self.settings = settings

    def run(self) -> None:
        """Execute the three phases in order: load, transform, save."""
        logger.info(f"[{self.name}] load")
        self.load()
        logger.info(f"[{self.name}] transform")
        self.transform()
        logger.info(f"[{self.name}] save")
        self.save()

    @abstractmethod
    def load(self) -> None:
        """Bring inputs into memory.

        May fetch from a remote source, read from local disk, or both.
        Disk locations are resolved via `self.settings.fp(...)`.
        """

    @abstractmethod
    def transform(self) -> None:
        """Turn the loaded inputs into the pipeline's output.

        Identity is allowed (e.g. a fetch pipeline that just persists raw
        bytes).
        """

    @abstractmethod
    def save(self) -> None:
        """Write the output to disk.

        May produce multiple files — the constraint is "one cohesive
        output", not "one file".
        """
