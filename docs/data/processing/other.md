# Other Sources

Beyond the EU Transaction Log itself (see [EU Transaction Log](eutl.md)), a few
auxiliary datasets are processed and joined onto the EUTL entities to make them
more usable. Each is produced by a pipeline module under `eutl_scraper/other/`
and follows the same acquire → extract → publish stages.

## Installation locations

The EUTL provides installation addresses but no coordinates. The
`InstallationLocationsBundle` (`eutl_scraper/other/locations/`) geocodes those
addresses into latitude/longitude pairs.

- A full address string is assembled from the installation's address lines,
  postal code, city, and country.
- Installations that have no meaningful fixed address are skipped: activity
  types **10** (aircraft) and **50** (shipping), and rows with no activity type.
- Geocoding can run against several services in parallel — **Geoapify**, **Google
  Maps**, and **OpenStreetMap** — one thread each. Each service tags its rows with
  its own `source`, so results from different providers can be compared or
  combined. Only Geoapify-derived coordinates are published; the Google Maps and
  OSM paths exist for cross-checking and are not distributed.
- An optional user-maintained cache of already-geocoded coordinates can be
  supplied. When present, API calls are suppressed **per service** for any
  `installation_id` already cached for that service, which avoids re-spending API
  quota on each run.

The published table holds `installation_id`, `lat`, `lon`, and the `source`
service, linking back to installations by `installation_id`.

## NACE codes

NACE codes classify installations by economic activity. They are **not** part of
the EUTL extracts; we recover them from the EU's carbon-**leakage lists**, which
enumerate installations together with their NACE Rev. 2 classification.

The `NaceFromLeakageListsBundle` (`eutl_scraper/other/nace_codes/`) uses three
static files bundled in the repository — no downloads are required:

- the **2015** leakage list (`leakage_2015.xlsx`),
- the **2020** leakage list (`leakage_2020.xlsx`), and
- an HTML export of the **NACE Rev. 2 scheme** (the code hierarchy and labels,
  from Eurostat RAMON).

> These leakage lists used to be downloadable but were removed from their
> original location, so the original files are kept in the code under
> `eutl_scraper/other/nace_codes/`.

Each list contributes a NACE code per installation (`nace_2015` and `nace_2020`,
keyed on the composite `installation_id`), and the two are merged so an
installation can carry a code from either vintage. Codes are normalised against
the official scheme to fix a common formatting quirk: some four-digit codes are
really a shorter-level code written with a trailing `.0` (e.g. `35.00` is the
two-digit class `35`), which is corrected so codes resolve cleanly against the
NACE hierarchy.

## Auction data

EUAs are also sold through primary-market **auctions** run by EEX. The
`EEXAuctionsBundle` (`eutl_scraper/other/eex_auctions/`) scrapes the
[EEX market-data hub](https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download)
and turns the published spreadsheets into a tidy table of auction results.

- The current-year **XLSX** is always fetched; a multi-year history **ZIP** can
  optionally be fetched and concatenated with it.
- The source spreadsheets are messy and inconsistent across years — header rows
  sit at varying positions, and column names differ between formats. The parser
  locates the header row dynamically and harmonises the many historical column
  spellings onto a single, stable set of names (prices, volumes, bid statistics,
  bidder counts, and revenue).
- **Per-country revenue** is handled in two layouts: newer files give a column
  per member state, while older files pack the breakdown into a single
  free-text "Auction Details" cell, which is parsed out into the same per-country
  columns. As a consistency check, the per-country revenues are summed and
  compared against the reported total (older pre-2016 rows sometimes lack a
  complete breakdown, so mismatches there are logged rather than treated as
  errors).

The result is one row per auction, with harmonised prices, volumes, and a
per-country revenue breakdown.

## Power plant and IED-facility mapping

EUTL installations can be linked to two further datasets: the power plants of the
**ENTSO-E Transparency Platform** and the industrial facilities of the EU's
**Industrial Emissions Portal (IEP)**, regulated under the Industrial Emissions
Directive (IED). The `EntsoeEidBundle` (`eutl_scraper/other/entsoe_eid/`) reads a
prepared set of mapping files bundled in the repository and writes them to the
extracted directory — the matching itself is done externally, and the methodology
is documented in the accompanying paper:

> Abrell, J., Kosch, M., and Stimpfle, L. (2025), *Linking EU ETS installations to
> ENTSO-E Power Plants and IEP Facilities*
> ([PDF](../../static/abrell_kosch_stimpfle_2025_linking_euets_entsoe_iep.pdf)).

Because the relationship between EUTL installations and ENTSO-E generation units is
**many-to-many**, an intermediate **power plant** entity resolves it. The bundle
produces four tables:

- **`powerplants`** — one row per power plant (`plant_id`, `fuel`), an aggregation
  of ENTSO-E generation and production units.
- **`map_entsoe_to_plant`** — links ENTSO-E generation (`eic_g`) and production
  (`eic_p`) units to their `plant_id`.
- **`map_installation_to_plant`** — links EUTL `installation_id`s to `plant_id`s.
- **`map_installation_to_eid_facility`** — links EUTL `installation_id`s to IEP
  facilities by their INSPIRE id (`facility_inspire_id`), together with a
  `match_probability`.
