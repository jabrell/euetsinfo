"""Frictionless `Resource` and `Package` construction.

`create_resource` wraps a prepared DataFrame as a Frictionless
`Resource`, loading table-level metadata (title, description, sources)
and the column schema from the YAML resource descriptor pointed to by
`table_config.schema_path`. `create_data_package` collects validated
resources, writes them to CSV alongside the `datapackage.{yaml,json}`
descriptors, and zips the result.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pandas as pd
import yaml
from frictionless import Package, Resource, Schema

from .configs import BaseConfig

PACKAGE_DOI = "10.5281/zenodo.20509231"

PACKAGE_LICENSES = [
    {
        "name": "CC-BY-4.0",
        "path": "https://creativecommons.org/licenses/by/4.0/",
        "title": "Creative Commons Attribution 4.0 International",
    }
]

PACKAGE_CONTRIBUTORS = [
    {
        "title": "Jan Abrell",
        "organization": "University of Basel",
        "path": "https://orcid.org/0000-0003-1435-0952",
        "role": "author",
    }
]

PACKAGE_DESCRIPTION = (
    "This data package compiles open data on the European Union Emissions "
    "Trading System (EU ETS) from several public sources, including the "
    "European Commission's EU Transaction Log (EUTL), the European Energy "
    "Exchange (EEX), the Eurostat NACE classification, the bundled carbon "
    "leakage lists, and geocoding services (Geoapify, Google Maps). The "
    "underlying source data remain the property of their respective providers "
    "and are subject to those providers' own reuse and licensing terms. The "
    "CC-BY-4.0 license declared for this package applies only to the "
    "compilation, structuring, and transformations contributed by the dataset "
    "authors, not to the underlying source data. Each resource lists its "
    "specific sources in its 'sources' field. When reusing this dataset, "
    "please attribute both the original sources and this compilation (see "
    "citation)."
)


def _build_citation(doi: str = PACKAGE_DOI) -> str:
    """Hardcoded dataset citation, appending the DOI when one is set."""
    base = (
        "Abrell, Jan (2026). EUTL Data Fetcher and Frictionless Package. "
        "University of Basel. https://github.com/jabrell/euetsinfo"
    )
    return f"{base} https://doi.org/{doi}" if doi else base


def _source_attribution(sources: list[dict[str, str]]) -> str:
    """Build a source-attribution sentence from a resource's sources."""
    credited = "; ".join(
        f"{s['title']} ({s['path']})" if s.get("path") else s["title"] for s in sources
    )
    return (
        f"Source data: {credited}. These data remain the property of their "
        "respective providers and are subject to those providers' own reuse "
        "and licensing terms; the package license (CC-BY-4.0) covers only the "
        "compilation and transformations contributed here."
    )


def create_resource(
    table_config: BaseConfig, df: pd.DataFrame, max_valid_rows: int = 10_000
) -> Resource:
    """Create a frictionless Resource from a DataFrame and a resource descriptor.

    The resource descriptor YAML at `table_config.schema_path` is expected to be
    a Frictionless Resource descriptor with top-level `name`, `title`,
    `description`, and `sources` keys, plus a nested `schema` key holding the
    Frictionless Table Schema (fields, primaryKey, foreignKeys, missingValues).
    This structure keeps all "what the table is" information in one file while
    leaving "how to produce it" (column renaming, type coercion) in the config.

    Args:
        table_config (BaseConfig): Configuration object for the table.
        df (pd.DataFrame): DataFrame to validate.
        max_valid_rows (int, optional): Maximum rows used for validation.
            Defaults to 10_000.

    Raises:
        Exception: If the validation fails, an exception is raised with details
            about the errors.
    """
    # Load the resource descriptor; feed only the nested schema to Frictionless
    # so top-level resource keys never pass through Schema.from_descriptor.
    descriptor = yaml.safe_load(table_config.schema_path.read_text(encoding="utf-8"))
    resource = Resource(
        data=df,
        name=table_config.name,
        title=descriptor["title"],
        description=descriptor["description"],
        sources=descriptor["sources"],
        encoding="utf-8",
        schema=Schema.from_descriptor(descriptor["schema"]),
    )

    # append a source-attribution note built from this resource's own sources
    if resource.description:
        resource.description = (
            f"{resource.description.rstrip()} "
            f"{_source_attribution(descriptor['sources'])}"
        )

    # validate the resource and raise an exception if validation fails
    report = resource.validate(limit_rows=max_valid_rows)
    if not report.valid:
        raise Exception(
            f"Validation failed for {table_config.name}: "
            f"\n{report.flatten(['rowNumber', 'fieldNumber', 'message'])}"
        )

    return resource


def create_data_package(
    resources: list[Resource],
    fn_out: Path,
    name: str,
) -> Package:
    """Write a list of Resources as a zipped Frictionless Data Package.

    Each resource is serialised to a CSV named after its `resource.name`,
    the package descriptor is written as both YAML and JSON, and all
    files are zipped into `fn_out`.

    Args:
        resources (list[Resource]): Resources to include in the Data
            Package.
        fn_out (Path): Path to write the output ZIP file to.
        name (str): Name of the Data Package descriptor.

    Returns:
        Package: The Frictionless `Package` object describing the bundle.
    """
    with TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Write CSVs
        for resource in resources:
            csv_path = tmp / f"{resource.name}.csv"
            resource.data.to_csv(
                csv_path, index=False, encoding="utf-8", date_format="%Y-%m-%dT%H:%M:%S"
            )
            # adjust the metadata of the resource to point to the CSV file
            resource.path = f"{resource.name}.csv"
            resource.format = "csv"
            resource.mediatype = "text/csv"
            resource.data = None

        # Build package descriptor
        package = Package(
            name=name,
            resources=resources,
            description=PACKAGE_DESCRIPTION,
            licenses=PACKAGE_LICENSES,
            contributors=PACKAGE_CONTRIBUTORS,
            homepage="https://github.com/jabrell/euetsinfo",
        )
        # DOI -> standard Data Package `id` field (only when one is set)
        if PACKAGE_DOI:
            package.id = f"https://doi.org/{PACKAGE_DOI}"
        # citation is not a standard Data Package field -> custom property
        package.custom["citation"] = _build_citation()
        package.to_yaml(str(tmp / "datapackage.yaml"))
        package.to_json(str(tmp / "datapackage.json"))

        # Zip everything
        with ZipFile(fn_out, "w") as zf:
            for file in tmp.iterdir():
                zf.write(file, arcname=file.name)

    return package
