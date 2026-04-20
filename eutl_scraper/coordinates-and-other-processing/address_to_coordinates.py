import time, os
import requests
import pandas as pd
from tqdm import tqdm

GEOAPIFY_API_KEY = 'TODO'
GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/search"

DIRNAME = os.path.dirname(__file__)
INPUT_CSV = os.path.join(DIRNAME, "data", "eutl_installations.csv")
OUTPUT_CSV = os.path.join(DIRNAME, "data", "eutl_installations-output.csv")

def clean_part(value):
    if pd.isna(value):
        return None
    value = str(value).strip()
    if value == "" or value == "-":
        return None
    return value

def build_full_address(row):
    parts = []

    # Address lines
    addr1 = clean_part(row.get("address1"))
    addr2 = clean_part(row.get("address2"))

    if addr1:
        parts.append(addr1)
    if addr2:
        parts.append(addr2)

    # Location details
    postal_code = clean_part(row.get("postal_code"))
    city = clean_part(row.get("city"))
    country = clean_part(row.get("registry_name"))

    city_block = ", ".join(p for p in [postal_code, city] if p)
    if city_block:
        parts.append(city_block)

    if country:
        parts.append(country)

    return ", ".join(parts)


def geocode_address(address: str):
    if pd.isna(address) or not address.strip():
        return None, None

    params = {
        "text": address,
        "limit": 1,
        "format": "json",
        "apiKey": GEOAPIFY_API_KEY,
    }

    r = requests.get(GEOAPIFY_URL, params=params, timeout=10)
    r.raise_for_status()

    data = r.json()
    if not data.get("results"):
        return None, None

    res = data["results"][0]
    return res.get("lat"), res.get("lon")

# Output
new_rows = []

# Existing CSV
existing_df = pd.read_csv(OUTPUT_CSV) if os.path.exists(OUTPUT_CSV) else pd.DataFrame()
fetched_installations = {}
for row in existing_df.to_dict('records'):
    fetched_installations[row["installation_id"]] = row
    new_rows.append(row)
    
# --- Load CSV ---
df = pd.read_csv(INPUT_CSV)

# Ensure columns exist
for col in ["lat", "lon"]:
    if col not in df.columns:
        df[col] = None

# Rows that need geocoding
mask = df["lat"].isna() | df["lon"].isna()

# Optional cache to avoid duplicate calls
cache = {}

df["full_address"] = df.apply(build_full_address, axis=1)
df = df[df["activity_type_code"] != 10]
df = df[df["activity_type_code"] != 50]

try:

    for row in tqdm(df.to_dict('records')):
        if row["installation_id"] in fetched_installations:
            continue
        
        if  str(row["activity_type_code"]) in ["10", "50"]:
            continue
        
        address = row["full_address"]

        if address in cache:
            lat, lon = cache[address]
        else:
            try:
                lat, lon = geocode_address(address)
                cache[address] = (lat, lon)
                time.sleep(0.25)  # rate-limit safety
            except Exception as e:
                print(f"✖ Failed: {address} → {e}")
                continue

        new_rows.append({
            **row,
            "lat": lat,
            "lon": lon
        })
        print(f"✔ Geocoded: {address}")
except e:
    print(e)
    print("Exiting...")
finally:
    # --- Save result ---
    pd.DataFrame(new_rows).to_csv(OUTPUT_CSV, index=False)

print("Done.")
