from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import pandas as pd
from frictionless import Package, Resource, Schema

from .configs import BaseConfig


def create_resource(
    table_config: BaseConfig, df: pd.DataFrame, max_valid_rows: int = 10_000
) -> Resource:
    """Create a frictionless Resource from a DataFrame and a schema definition.

    Args:
        table_config (BaseConfig): Configuration object for the table.
        df (pd.DataFrame): DataFrame to validate.
        max_valid_rows (int, optional): Maximum rows used for validation.
            Defaults to 10_000.

    Raises:
        Exception: If the validation fails, an exception is raised with details
            about the errors.
    """
    fn_schema = table_config.schema_path
    resource = Resource(data=df, schema=Schema.from_descriptor(fn_schema))

    # add the package metadata
    resource.name = table_config.name
    for key, value in vars(table_config.resource_metadata).items():
        setattr(resource, key, value)

    # validate the resource and raise an exception if validation fails
    report = resource.validate(limit_rows=max_valid_rows)
    if not report.valid:
        raise Exception(
            f"Validation failed for {table_config.name}: "
            f"\n{report.flatten(['rowNumber', 'fieldNumber', 'message'])}"
        )

    return resource


def create_data_package(
    resources: dict[str, Resource],
    fn_out: Path,
    name: str,
) -> Package:
    """Create a frictionless Data Package from a list of Resources and save
    it as a zip file.

    Args:
        resources (dict[str, Resource]): Dictionary of Resources to include in the
            Data Package.
        fn_out (Path): Path to save the output zip file.
        name (str): Name of the Data Package.

    Returns:
        Package: The created Data Package object.
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
        package = Package(name=name, resources=resources)
        package.to_yaml(str(tmp / "datapackage.yaml"))
        package.to_json(str(tmp / "datapackage.json"))

        # Zip everything
        with ZipFile(fn_out, "w") as zf:
            for file in tmp.iterdir():
                zf.write(file, arcname=file.name)

    return package
