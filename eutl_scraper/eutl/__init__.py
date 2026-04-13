"""This module contains the main functions for the EUTL scraper. It provides
functions to download, extract and normalize the EUTL dataset as provided by
by the European Commission: https://union-registry-data.ec.europa.eu/report/welcome
"""

from .download import download_all_data
from .extract import extract_all_data
from .normalize import normalize_all_data
from .pipeline import EUTLPipelineSteps, pipeline_eutl

__all__ = [
    "EUTLPipelineSteps",
    "pipeline_eutl",
    "download_all_data",
    "extract_all_data",
    "normalize_all_data",
]
