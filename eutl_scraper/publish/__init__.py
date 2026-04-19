"""The publish module contains functions to publish the data extracted and
processed by the scraper."""

import warnings

from .data_package import publish_data_package
from .prepare_tables import prepare_table
from .resources import create_data_package, create_resource
from .table_registry import TABLE_REGISTRY

# Ignore warnings about incompatible versions of urllib3 and chardet, which are
# dependencies of frictionless. This is a known issue of requests and can be safely
# ignored.
warnings.filterwarnings(
    "ignore", message="urllib3.*or chardet.*doesn't match a supported version"
)

__all__ = [
    "TABLE_REGISTRY",
    "prepare_table",
    "create_resource",
    "create_data_package",
    "publish_data_package",
]
