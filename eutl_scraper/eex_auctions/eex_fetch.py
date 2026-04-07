import hashlib
import json
import os
import zipfile
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup


def update_eex_auction_prices(
    eex_url: str,
    data_dir: str,
    prices_filename: str = "eex_auction_prices.xlsx",
    meta_filename: str = "eex_top_xlsx_meta.json",
    download_zip: bool = False,
) -> pd.DataFrame:
    """
    Incrementally update EEX EUA primary auction price data.

    This function retrieves the latest EUA primary auction price data from the
    European Energy Exchange (EEX) website, extracts the auction date and price
    from the top-level Excel file, and merges any newly available observations
    into a locally stored dataset without overwriting existing data (2012-today).

    The update process is incremental:
    - If the remote Excel file has not changed since the last run (based on
      HTTP headers or file hash comparison), no download or update is performed.
    - If new or revised data are detected, only the affected rows are merged
      into the existing dataset.

    Column headers and file formats are normalized automatically to account
    for historical inconsistencies in EEX data exports.


    Args:
        eex_url (str): URL of the EEX web page that hosts the EUA primary auction
            data downloads. The function automatically discovers the current Excel
            download link.
        data_dir (str): Base directory used to store intermediate files and outputs
            related to the EEX auction price dataset. The final dataset is written to
            the the EEX auction price dataset. The final dataset is written to the
            ``output`` subdirectory of this folder.
        prices_filename (str, optional): Name of the Excel file containing the
            consolidated auction price time series.
            Defaults to ``"eex_auction_prices.xlsx"``.
        meta_filename (str, optional): Name of the JSON metadata file used to track
            the previously downloaded version of the Excel source (ETag, Last-Modified,
            content hash).
            Defaults to ``"eex_top_xlsx_meta.json"``.
        download_zip (bool, optional): If ``True``, the function also downloads
            the first ZIP archive found on the EEX page, extracts any Excel files
            contained within it, and deletes the archive afterwards. This is intended
            for historical backfills and is disabled by default.

    Returns:
        pandas.DataFrame
            A DataFrame containing the consolidated EUA primary auction price time
            series with the following columns:

            - ``Date`` : datetime.date
            Auction date (time component removed).
            - ``Auction Price €/tCO2`` : float
            Auction clearing price in EUR per tonne of CO₂.

            The returned DataFrame is sorted by date in ascending order.
    """

    # -------------------------
    # folders / paths
    # -------------------------
    raw_dir = os.path.join(data_dir, "raw")
    output_dir = os.path.join(data_dir, "output")
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    prices_path = os.path.join(output_dir, prices_filename)
    meta_path = os.path.join(output_dir, meta_filename)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # -------------------------
    # helpers
    # -------------------------
    def sha256_file(path: str) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def download_file(url: str, dest_path: str):
        with requests.get(url, headers=headers, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)

    def excel_engine(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".xlsx":
            return "openpyxl"
        if ext == ".xls":
            return "xlrd"
        raise RuntimeError(f"Unsupported extension: {ext}")

    def find_first_xlsx_and_zip(page_url: str):
        resp = requests.get(page_url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        xlsx_url = None
        zip_url = None

        for a in soup.find_all("a", href=True):
            href_raw = a["href"].strip()
            href = href_raw.lower()

            if href.endswith(".xlsx") and xlsx_url is None:
                xlsx_url = urljoin(page_url, href_raw)
            elif href.endswith(".zip") and zip_url is None:
                zip_url = urljoin(page_url, href_raw)

            if xlsx_url and zip_url:
                break

        if not xlsx_url:
            raise RuntimeError("No XLSX found on the page.")
        if download_zip and not zip_url:
            raise RuntimeError("download_zip=True but no ZIP found on the page.")

        return xlsx_url, zip_url

    def unzip_keep_only_excel(zip_path: str, target_dir: str):
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.infolist():
                if not member.filename.lower().endswith((".xlsx", ".xls")):
                    continue
                filename = os.path.basename(member.filename)
                if not filename:
                    continue

                target_path = os.path.join(target_dir, filename)

                # Keep existing raw files stable
                if os.path.exists(target_path):
                    continue

                with z.open(member) as source, open(target_path, "wb") as target:
                    target.write(source.read())

    def detect_header_row(df_preview: pd.DataFrame) -> int | None:
        for i in range(len(df_preview)):
            row = df_preview.iloc[i].astype(str).str.strip().str.lower()
            # substring detection
            if row.str.contains("date", na=False).any():
                return i
        return None

    def extract_prices_from_excel(file_path: str) -> pd.DataFrame:
        eng = excel_engine(file_path)
        xls = pd.ExcelFile(file_path, engine=eng)

        last_error = None
        for sheet in xls.sheet_names:
            try:
                preview = pd.read_excel(
                    file_path,
                    sheet_name=sheet,
                    header=None,
                    nrows=120,
                    engine=eng,
                )
                header_row = detect_header_row(preview)
                if header_row is None:
                    continue

                df = pd.read_excel(
                    file_path,
                    sheet_name=sheet,
                    header=header_row,
                    engine=eng,
                )

                # Clean column names
                df.columns = df.columns.astype(str).str.strip().str.replace("\n", " ")

                # Normalize known column header variant
                df.columns = [
                    c.replace("Auction Price EUR/tCO2", "Auction Price €/tCO2")
                    for c in df.columns
                ]

                # Date column
                date_col = next(
                    (c for c in df.columns if str(c).strip().lower() == "date"), None
                )
                if date_col is None:
                    date_col = next(
                        (c for c in df.columns if "date" in str(c).lower()), None
                    )

                # Price column
                if "Auction Price €/tCO2" in df.columns:
                    price_col = "Auction Price €/tCO2"
                else:
                    price_col = None
                    for c in df.columns:
                        cl = str(c).lower()
                        if "auction" in cl and "price" in cl:
                            price_col = c
                            break

                if not date_col or not price_col:
                    continue

                out = df[[date_col, price_col]].copy()
                out = out.rename(
                    columns={date_col: "Date", price_col: "Auction Price €/tCO2"}
                )

                out["Date"] = pd.to_datetime(out["Date"], errors="coerce").dt.date
                out["Auction Price €/tCO2"] = pd.to_numeric(
                    out["Auction Price €/tCO2"], errors="coerce"
                )
                out = out.dropna(subset=["Date", "Auction Price €/tCO2"])

                if len(out) == 0:
                    continue

                return out

            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(
            f"Could not extract Date/Auction Price from {os.path.basename(file_path)}"
            f"; last_error={last_error}"
        )

    def parse_all_raw_excel(folder: str) -> pd.DataFrame:
        excel_files = [
            f for f in os.listdir(folder) if f.lower().endswith((".xlsx", ".xls"))
        ]
        print(f"Raw Excel files found: {len(excel_files)}")

        all_dfs = []
        for fn in excel_files:
            fp = os.path.join(folder, fn)
            try:
                tmp = extract_prices_from_excel(fp)
                tmp["source_file"] = fn
                all_dfs.append(tmp)
            except Exception as e:
                # Keep going; but print so you can see what's skipped
                print(f"Skipping {fn}: {e}")

        if not all_dfs:
            return pd.DataFrame(columns=["Date", "Auction Price €/tCO2", "source_file"])

        combined = pd.concat(all_dfs, ignore_index=True)
        combined = combined.drop_duplicates(subset=["Date"], keep="last").sort_values(
            "Date"
        )
        return combined

    # -------------------------
    # main
    # -------------------------
    xlsx_url, zip_url = find_first_xlsx_and_zip(eex_url)
    print("XLSX:", xlsx_url)
    if download_zip:
        print("ZIP :", zip_url)

    # load meta (optional)
    old_meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            old_meta = json.load(f)

    # -------- download latest XLSX to raw (only if changed by headers) --------
    head = requests.head(xlsx_url, headers=headers, allow_redirects=True, timeout=30)
    etag = head.headers.get("ETag")
    last_modified = head.headers.get("Last-Modified")

    latest_name = os.path.basename(urlparse(xlsx_url).path)
    latest_raw_path = os.path.join(raw_dir, latest_name)

    same_by_headers = (
        old_meta.get("xlsx_url") == xlsx_url
        and old_meta.get("etag") == etag
        and old_meta.get("last_modified") == last_modified
        and (etag or last_modified)
        and os.path.exists(latest_raw_path)
    )

    if not same_by_headers:
        print("Downloading latest XLSX...")
        download_file(xlsx_url, latest_raw_path)

    latest_hash = sha256_file(latest_raw_path)

    # -------- optional ZIP: download + extract into raw --------
    zip_hash = None
    if download_zip and zip_url:
        zip_name = os.path.basename(urlparse(zip_url).path)
        zip_path = os.path.join(raw_dir, zip_name)

        if not os.path.exists(zip_path):
            print("Downloading ZIP...")
            download_file(zip_url, zip_path)

        zip_hash = sha256_file(zip_path)

        print("Extracting Excel files from ZIP...")
        unzip_keep_only_excel(zip_path, raw_dir)

        # delete zip after extraction
        os.remove(zip_path)
        print("ZIP processed and deleted.")

    # -------- parse AFTER zip extraction --------
    print("Parsing all raw Excel files (ZIP history + latest)...")
    consolidated = parse_all_raw_excel(raw_dir)

    try:
        latest_df = extract_prices_from_excel(latest_raw_path)
        latest_df["source_file"] = os.path.basename(latest_raw_path)
        consolidated = pd.concat([consolidated, latest_df], ignore_index=True)
        consolidated = consolidated.drop_duplicates(
            subset=["Date"], keep="last"
        ).sort_values("Date")
    except Exception as e:
        print("Warning: failed to re-apply latest XLSX overwrite logic:", e)

    consolidated.to_excel(prices_path, index=False, engine="openpyxl")
    print("Updated:", prices_path)

    # update meta
    new_meta = {
        "xlsx_url": xlsx_url,
        "etag": etag,
        "last_modified": last_modified,
        "sha256_latest_xlsx": latest_hash,
        "sha256_zip": zip_hash,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(new_meta, f, indent=2)

    return consolidated
