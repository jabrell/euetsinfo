import logging

import pandas as pd

MAP_COLUMN_NAMES = {
    # --- Core ---
    "Date": "date",
    "Time": "time",
    "Auction Time": "time",
    "Auction Name": "auction_name",
    "Contract": "contract",
    "Certificate": "certificate",
    "Status": "status",
    "Country": "country",
    # --- Prices ---
    "Auction Price €/tCO2": "auction_price_eur_per_tco2",
    "Minimum Bid €/tCO2": "minimum_bid_eur_per_tco2",
    "Minimum Bid EUR/tCO2": "minimum_bid_eur_per_tco2",
    "Minimal Price €/tCO2": "minimum_bid_eur_per_tco2",
    "Maximum Bid €/tCO2": "maximum_bid_eur_per_tco2",
    "Maximum Bid EUR/tCO2": "maximum_bid_eur_per_tco2",
    "Maximal Price €/tCO2": "maximum_bid_eur_per_tco2",
    "Mean €/tCO2": "mean_price_eur_per_tco2",
    "Mean Price EUR/tCO2": "mean_price_eur_per_tco2",
    "Median €/tCO2": "median_price_eur_per_tco2",
    "Median Price EUR/tCO2": "median_price_eur_per_tco2",
    # --- Volume & bids ---
    "Auction Volume tCO2": "auction_volume_tco2",
    "Auction Volume": "auction_volume_tco2",
    "Total Amount of Bids": "total_amount_of_bids",
    "Number of bids submitted": "number_of_bids_submitted",
    "Number of successful bids": "number_of_successful_bids",
    "Average number of bids per bidder": "average_bids_per_bidder",
    "Average bid size": "average_bid_size",
    "Average volume bid per bidder": "average_volume_bid_per_bidder",
    "Standard deviation of bid volume per bidder": (
        "standard_deviation_bid_volume_per_bidder"
    ),
    "Average volume won per bidder": "average_volume_won_per_bidder",
    "Standard deviation of volume won per bidder": (
        "standard_deviation_volume_won_per_bidder"
    ),
    "Cover Ratio": "cover_ratio",
    # --- Bidders ---
    "Total Number of Bidders": "total_number_of_bidders",
    "Number of Successful Bidders": "number_of_successful_bidders",
    "Number of Succesful  Bidders": "number_of_successful_bidders",
    # --- Revenue ---
    "Total Revenue €": "total_revenue_eur",
    "Total Revenue EUR": "total_revenue_eur",
    # --- Country revenues (new format) ---
    "Austria (AT)": "revenue_at_eur",
    "Belgium (BE)": "revenue_be_eur",
    "Bulgaria (BG)": "revenue_bg_eur",
    "Cyprus (CY)": "revenue_cy_eur",
    "Czech Republic (CZ)": "revenue_cz_eur",
    "Germany (DE)": "revenue_de_eur",
    "Denmark (DK)": "revenue_dk_eur",
    "Estonia (EE)": "revenue_ee_eur",
    "Greece (EL)": "revenue_el_eur",
    "Spain (ES)": "revenue_es_eur",
    "Finland (FI)": "revenue_fi_eur",
    "France (FR)": "revenue_fr_eur",
    "Croatia (HR)": "revenue_hr_eur",
    "Hungary (HU)": "revenue_hu_eur",
    "Ireland (IE)": "revenue_ie_eur",
    "Iceland (IS)": "revenue_is_eur",
    "Italy (IT)": "revenue_it_eur",
    "Liechtenstein (LI)": "revenue_li_eur",
    "Lithuania (LT)": "revenue_lt_eur",
    "Luxembourg (LU)": "revenue_lu_eur",
    "Latvia (LV)": "revenue_lv_eur",
    "Malta (MT)": "revenue_mt_eur",
    "Netherlands (NL)": "revenue_nl_eur",
    "Norway (NO)": "revenue_no_eur",
    "Poland (PL)": "revenue_pl_eur",
    "Portugal (PT)": "revenue_pt_eur",
    "Romania (RO)": "revenue_ro_eur",
    "Sweden (SE)": "revenue_se_eur",
    "Slovenia (SI)": "revenue_si_eur",
    "Slovakia (SK)": "revenue_sk_eur",
    "Northern Ireland (XI)": "revenue_xi_eur",
    # --- Country revenues (old format, from Auction Details) ---
    "revenues_AT": "revenue_at_eur",
    "revenues_BE": "revenue_be_eur",
    "revenues_BG": "revenue_bg_eur",
    "revenues_CY": "revenue_cy_eur",
    "revenues_CZ": "revenue_cz_eur",
    "revenues_DK": "revenue_dk_eur",
    "revenues_EE": "revenue_ee_eur",
    "revenues_EL": "revenue_el_eur",
    "revenues_ES": "revenue_es_eur",
    "revenues_FI": "revenue_fi_eur",
    "revenues_FR": "revenue_fr_eur",
    "revenues_HR": "revenue_hr_eur",
    "revenues_HU": "revenue_hu_eur",
    "revenues_IE": "revenue_ie_eur",
    "revenues_IT": "revenue_it_eur",
    "revenues_LT": "revenue_lt_eur",
    "revenues_LU": "revenue_lu_eur",
    "revenues_LV": "revenue_lv_eur",
    "revenues_MT": "revenue_mt_eur",
    "revenues_NL": "revenue_nl_eur",
    "revenues_PT": "revenue_pt_eur",
    "revenues_RO": "revenue_ro_eur",
    "revenues_SE": "revenue_se_eur",
    "revenues_SI": "revenue_si_eur",
    "revenues_SK": "revenue_sk_eur",
    # --- Funds ---
    "Innovation Fund (IF)": "revenue_innovation_fund_eur",
    "Innovation Fund": "revenue_innovation_fund_eur",
    "InnoFund RRF (IX)": "revenue_innovation_fund_rrf_eur",
    "Modernisation Fund (MF)": "revenue_modernisation_fund_eur",
    "Social Climate Fund (SF)": "revenue_social_climate_fund_eur",
    "MS RRF (MX)": "revenue_ms_rrf_eur",
}

COLUMN_DTYPES = {
    # --- Core ---
    "date": "datetime64[ns]",
    "time": "datetime64[ns]",
    "datetime": "datetime64[ns]",
    "auction_name": "string",
    "contract": "string",
    "certificate": "string",
    "status": "string",
    "country": "string",
    # --- Prices ---
    "auction_price_eur_per_tco2": "Float64",
    "minimum_bid_eur_per_tco2": "Float64",
    "maximum_bid_eur_per_tco2": "Float64",
    "mean_price_eur_per_tco2": "Float64",
    "median_price_eur_per_tco2": "Float64",
    # --- Volume & bids ---
    "auction_volume_tco2": "Int64",
    "total_amount_of_bids": "Int64",
    "number_of_bids_submitted": "Int64",
    "number_of_successful_bids": "Int64",
    "average_bids_per_bidder": "Float64",
    "average_bid_size": "Float64",
    "average_volume_bid_per_bidder": "Float64",
    "standard_deviation_bid_volume_per_bidder": "Float64",
    "average_volume_won_per_bidder": "Float64",
    "standard_deviation_volume_won_per_bidder": "Float64",
    "cover_ratio": "Float64",
    # --- Bidders ---
    "total_number_of_bidders": "Int64",
    "number_of_successful_bidders": "Int64",
    # --- Revenue ---
    "total_revenue_eur": "Float64",
    "revenue_at_eur": "Float64",
    "revenue_be_eur": "Float64",
    "revenue_bg_eur": "Float64",
    "revenue_cy_eur": "Float64",
    "revenue_cz_eur": "Float64",
    "revenue_de_eur": "Float64",
    "revenue_dk_eur": "Float64",
    "revenue_ee_eur": "Float64",
    "revenue_el_eur": "Float64",
    "revenue_es_eur": "Float64",
    "revenue_fi_eur": "Float64",
    "revenue_fr_eur": "Float64",
    "revenue_hr_eur": "Float64",
    "revenue_hu_eur": "Float64",
    "revenue_ie_eur": "Float64",
    "revenue_is_eur": "Float64",
    "revenue_it_eur": "Float64",
    "revenue_li_eur": "Float64",
    "revenue_lt_eur": "Float64",
    "revenue_lu_eur": "Float64",
    "revenue_lv_eur": "Float64",
    "revenue_mt_eur": "Float64",
    "revenue_nl_eur": "Float64",
    "revenue_no_eur": "Float64",
    "revenue_pl_eur": "Float64",
    "revenue_pt_eur": "Float64",
    "revenue_ro_eur": "Float64",
    "revenue_se_eur": "Float64",
    "revenue_si_eur": "Float64",
    "revenue_sk_eur": "Float64",
    "revenue_xi_eur": "Float64",
    "revenue_innovation_fund_eur": "Float64",
    "revenue_innovation_fund_rrf_eur": "Float64",
    "revenue_modernisation_fund_eur": "Float64",
    "revenue_social_climate_fund_eur": "Float64",
    "revenue_ms_rrf_eur": "Float64",
}


def find_column(df: pd.DataFrame, name: str) -> str | None:
    """Little helper to find a column in a DataFrame by name, ignoring case and
    whitespace.

    Args:
        df: The DataFrame to search for the column.
        name: The name of the column to find.
    Returns:
        The actual column name in the DataFrame, or None if no matching column
        is found.
    """
    cols = df.columns.astype(str).str.strip().str.lower()
    exact = cols == name
    if exact.any():
        return df.columns[exact.argmax()]
    partial = cols.str.contains(name, na=False)
    if partial.any():
        return df.columns[partial.argmax()]
    return None


def parse_auction_details(details: str) -> dict[str, float]:
    """Parse an 'Auction Details' cell into a {country_code: value} dict.

    Args:
        details (str): The 'Auction Details' cell content.

    Returns:
        A dictionary with country codes as keys and corresponding values as floats.
    """
    text = str(details).strip()
    # normalize: some entries use commas, others use newlines
    text = text.replace("\n", ",")
    result = {}
    for part in text.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        key, val = part.split(":", 1)
        val = val.strip().replace(".", "")  # remove thousand separators
        result[f"revenues_{key.strip()}"] = float(val)
    return result


def explode_auction_details(df: pd.DataFrame) -> pd.DataFrame:
    """Explode the 'Auction Details' column into separate columns for each
    country code.

    Args:
        df: The DataFrame containing the 'Auction Details' column.

    Returns:
        A new DataFrame with the 'Auction Details' column exploded into separate
        columns for each country code.
    """
    col = find_column(df, "auction details")
    if col is None:
        return df

    mask = df[col].notna() & (df[col].astype(str).str.strip() != "")
    df_old = df[mask].copy()
    df_new = df[~mask].copy()

    if not df_old.empty:
        details = df_old[col].apply(parse_auction_details).apply(pd.Series)
        df_old = pd.concat([df_old.drop(columns=[col]), details], axis=1)

    df_new = df_new.drop(columns=[col])

    return pd.concat([df_old, df_new], ignore_index=True)


def harmonize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonize column names in the DataFrame by renaming known columns and
    merging duplicates.

    Args:
        df: The DataFrame to harmonize.

    Returns:
        A DataFrame with harmonized column names.
    """
    # rename known columns
    df = df.rename(
        columns={c: MAP_COLUMN_NAMES[c] for c in df.columns if c in MAP_COLUMN_NAMES}
    )

    # merge duplicate columns (old + new mapped to the same target)
    # combine duplicate columns, keeping first non-null value (assuming old and
    # new format don't overlap)
    df = df.T.groupby(level=0).first().T

    return df


def check_revenue_totals(df: pd.DataFrame, atol: float = 1.0) -> None:
    """Check that the sum of the country revenues matches the total revenue for
    each row, within a specified absolute tolerance.

    Note: For some older data 2016 and before, the country breakdown is sometimes
        missing or incomplete, so this check may fail for those rows.

    Args:
        df: The DataFrame containing the revenue data.
            Must have a 'total_revenue_eur' column.
        atol: The absolute tolerance for comparing the sum of country revenues to
            the total revenue. Defaults to 1.0 (i.e., 1 euro).
    """
    revenue_cols = [
        c for c in df.columns if c.startswith("revenue_") and c != "total_revenue_eur"
    ]
    has_breakdown = df[revenue_cols].notna().any(axis=1)
    mask = df["total_revenue_eur"].notna() & has_breakdown

    computed = df.loc[mask, revenue_cols].sum(axis=1)
    expected = df.loc[mask, "total_revenue_eur"]

    diff = (computed - expected).abs()
    bad = diff > atol

    if bad.any():
        logging.warning(
            f"Revenue mismatch in {bad.sum()} rows (of {mask.sum()}): "
            f"{diff[bad].describe()}"
        )
    else:
        logging.info(f"All {mask.sum()} rows pass revenue check (atol={atol})")


def enforce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Enforce consistent data types for the columns in the DataFrame.

    Args:
        df: The DataFrame to enforce data types on.

    Returns:
        A DataFrame with enforced data types."""
    df_ = df.copy()
    for col, dtype in COLUMN_DTYPES.items():
        if col not in df_.columns:
            continue
        if dtype.startswith("datetime"):
            df_[col] = pd.to_datetime(df_[col], format="mixed", errors="coerce")
        else:
            df_[col] = df_[col].astype(dtype)
    return df_


def parse_auctions(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the raw DataFrame extracted from the Excel files,
    harmonize column names, and perform consistency checks.

    Args:
        df: The raw DataFrame to parse.

    Returns:
        A cleaned and parsed DataFrame ready for analysis.
    """
    df = explode_auction_details(df)
    df = harmonize_columns(df)
    check_revenue_totals(df)

    # format the date columns
    dates = pd.to_datetime(df["date"]).dt.normalize()
    times = pd.to_timedelta(
        pd.to_datetime(df["time"], format="mixed").dt.time.astype(str)
    )
    df["datetime"] = dates + times

    # replace missings by NaNs
    df = df.replace(["None", "none", "nan", ""], pd.NA).fillna(pd.NA)

    # ensure consistent data types
    df = enforce_dtypes(df)
    return df
