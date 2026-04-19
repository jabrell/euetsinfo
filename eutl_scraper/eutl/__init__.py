"""This module contains the main functions for the EUTL scraper. It provides
functions to download, extract and normalize the EUTL dataset as provided by
by the European Commission: https://union-registry-data.ec.europa.eu/report/welcome
"""

from .download import download_all
from .extract import extract_all
from .pipeline import EUTLPipelineSteps, pipeline_eutl

__all__ = [
    "EUTLPipelineSteps",
    "pipeline_eutl",
    "download_all",
    "extract_all",
]
