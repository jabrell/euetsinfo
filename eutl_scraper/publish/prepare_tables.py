"""Apply a table's publication config to its extracted DataFrame.

`prepare_table` is the first step of `publish_data_package`: it runs the
column-level type converters, then the DataFrame-level transformers, and
finally applies the column renaming and selection declared by the
config. The result is a DataFrame whose columns match the published
Frictionless schema and is ready for `create_resource`.
"""

import pandas as pd

from .configs import BaseConfig


def prepare_table(table_config: BaseConfig, df: pd.DataFrame) -> pd.DataFrame:
    """Prepare an extracted table for publication.

    Applies, in order: the per-column `type_convertors`, the
    DataFrame-level `transformers`, and finally the `column_mapping`
    rename followed by selection of only the mapped (published) columns.

    Args:
        table_config (BaseConfig): Configuration object for the table.
        df (pd.DataFrame): DataFrame containing the extracted data for
            this table.

    Returns:
        pd.DataFrame: DataFrame with published column names and types,
            restricted to the columns declared in
            `table_config.column_mapping`.
    """
    # ensure correct types
    type_convertors = table_config.type_convertors
    for column, convertor in type_convertors.items():
        df[column] = convertor(df)

    # apply any additional transformations defined in the config
    for transformer in table_config.transformers:
        df = transformer(df)

    # rename columns and select only the columns defined in the schema
    map_installation_columns = table_config.column_mapping

    df_inst = df.rename(columns=map_installation_columns)[
        list(map_installation_columns.values())
    ]
    return df_inst
