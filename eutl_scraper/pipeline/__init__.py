"""The pipeline module defines the abstract interface for pipelines. Each
pipeline takes a settings object and executes a series of steps to process the
data. The specific steps and their implementation are defined in the respective
pipeline modules. The settings object defines the file configuration, i.e., where
to read the input data from and where to save the output data to."""

from abc import ABC, abstractmethod

from ..settings import Settings


class BasePipeline(ABC):
    def __init__(self, settings: Settings, **kwargs):
        self.settings = settings

    @abstractmethod
    def run(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the run method.")

    @abstractmethod
    def fetch(self, *args, **kwargs):
        """Fetch data from a remote server and save it to disk."""
        raise NotImplementedError("Subclasses must implement the fetch method.")

    @abstractmethod
    def load(self, *args, **kwargs):
        """Load data from disk into memory."""
        raise NotImplementedError("Subclasses must implement the load method.")

    @abstractmethod
    def extract(self, *args, **kwargs):
        """Extract relevant information from the transformed data."""
        raise NotImplementedError("Subclasses must implement the extract method.")

    @abstractmethod
    def save(self, *args, **kwargs):
        """Save the extracted data to disk."""
        raise NotImplementedError("Subclasses must implement the save method.")

    @abstractmethod
    def augment(self, *args, **kwargs):
        """Post processing step to augment the extracted data with additional
        information."""
        raise NotImplementedError("Subclasses must implement the augment method.")
