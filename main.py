import pandas as pd
from eutl_scraper.download import download_installations, download_compliance
from eutl_scraper.normalize import normalize_installations, normalize_compliance
from eutl_scraper.extract import extract_installations, extract_compliance


def create_installation_table(fn_out: str | None = None) -> pd.DataFrame:
    """Create the installation table by downloading, normalizing, and
    extracting installation data.

    Args:
        fn_out (str | None, optional): Output filename to save the installation data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing installation data.
    """
    df = (
        download_installations()
        .pipe(normalize_installations)
        .pipe(extract_installations, fn_out=fn_out)
    )
    return df


def create_compliance_table(fn_out: str | None = None) -> pd.DataFrame:
    """Create the compliance table by downloading, normalizing, and
    extracting compliance data.

    Args:
        fn_out (str | None, optional): Output filename to save the compliance data.
            Defaults to None.

    Returns:
        pd.DataFrame: DataFrame containing compliance data.
    """
    df = (
        download_compliance()
        .pipe(normalize_compliance)
        .pipe(extract_compliance, fn_out=fn_out)
    )
    return df


if __name__ == "__main__":
    dir_extracted = "data/extracted"
    df_installations = create_installation_table(
        fn_out=f"{dir_extracted}/eutl_installations.csv"
    )
    df_compl = create_compliance_table(fn_out=f"{dir_extracted}/eutl_compliance.csv")
    print("done")
