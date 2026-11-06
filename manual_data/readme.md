This folder also contains data that have been manually downloaded from the
[PowerBi app](https://union-registry-data.ec.europa.eu/report/welcome).
As a general rule, be careful with the manual downloads in checking:

1. No filters are applied, in particular, check that you download both active and inactive accounts.
2. The download restriction (150'000) rows do not affect the download.

Only the account data (not the operator holding accounts) are needed to create the
data (location: *Emission Trading System -> Accounts*)

## Installation locations

- `coordinates_geoapify.csv` — cache of already-geocoded Geoapify coordinates
  (`source=geoapify`). Registered as `existing_installation_locations` in
  `Settings.manual_files`; suppresses repeated Geoapify API calls for cached
  installations.
- `bruegel_manual.csv` — manually curated installation coordinates provided by
  Bruegel. Passed to `AllDataBundle` via
  `manual_location_entries={"manual_bruegel": ...}` and published under the
  source `manual_bruegel`. Required columns: `installation_id`, `latitude`,
  `longitude`, `created_at` (ISO 8601); no `source` column. The coordinate
  quality is the responsibility of the provider.
- `manual_coordinate_changes.csv` — original comparison file from which
  `bruegel_manual.csv` was derived. `lat_csv`/`lon_csv` are the previous
  Geoapify coordinates, `lat_db`/`lon_db` the Bruegel coordinates. Only rows
  with Bruegel coordinates (609) were taken over; `created_at` was set to
  2026-10-13, the date the data were added.
