import pandas as pd


def _strip_str(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from string columns in the DataFrame.

    Args:
        df (pd.DataFrame): Input DataFrame.

    Returns:
        pd.DataFrame: DataFrame with whitespace stripped from string columns.
    """
    df = df.copy()
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    df[str_cols] = df[str_cols].apply(lambda x: x.str.strip())
    return df
