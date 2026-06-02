"""Publication layer for the EUTL scraper.

Turns the cleaned parquet tables in `Settings.dir_extracted` into a
[Frictionless Data Package](https://specs.frictionlessdata.io/) — a ZIP
bundle of CSV files plus a `datapackage.{yaml,json}` descriptor.

Flow:

1. `TABLE_REGISTRY` maps a table name to a `BaseConfig` subclass that
   declares column renaming, type conversion, additional transformers,
   resource metadata, and the path to the YAML Frictionless schema.
2. `prepare_table` applies type converters, transformers, and the column
   mapping to the source DataFrame.
3. `create_resource` wraps the prepared DataFrame as a Frictionless
   `Resource`, attaches the metadata, and validates it against the
   schema.
4. `create_data_package` writes the resources as CSVs together with the
   descriptor files into a ZIP archive.

`publish_data_package` orchestrates the four steps for every table in the
registry.
"""

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
