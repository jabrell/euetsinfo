import pandas as pd

from .configs import BaseConfig


def prepare_table(table_config: BaseConfig, df: pd.DataFrame) -> pd.DataFrame:
    """Use the extracted installation data to and prepare a table resource for
    publication by renaming columns, changing data types, and adding a primary key.

    Args:
        table_config (BaseConfig): Configuration object for the table.
        df (pd.DataFrame): DataFrame containing the extracted installation data.

    Returns:
        pd.DataFrame: DataFrame containing the prepared installation data.
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
