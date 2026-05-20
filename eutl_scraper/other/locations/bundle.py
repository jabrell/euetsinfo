"""Installation locations pipeline.

Orchestrates the existing service modules in this package:

- `get_installation_coordinates_google`   (`.google_coordinates`)
- `get_installation_coordinates_geoapify` (`.geoapify_coordinates`)
- `get_installation_coordinates_osm`      (`.osm_coordinates`)

Runs the configured services in parallel (one thread per service) and
skips, per service, any `installation_id` that already has a row for that
service in the user-supplied existing-locations CSV. The 10/50
activity-type filter is applied once up front.

Two classes:

- `ExtractInstallationLocationsPipeline` — single pipeline producing the
  combined locations table.
- `InstallationLocationsBundle` — thin Bundle wrapper that surfaces
  `api_keys` and `max_installations` at the source-level entry point.
"""

import concurrent.futures
from typing import Callable

import pandas as pd
from loguru import logger

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import Settings

from .geoapify_coordinates import get_installation_coordinates_geoapify
from .google_coordinates import get_installation_coordinates_google
from .osm_coordinates import get_installation_coordinates_osm

# Map service-key (used in api_keys + tagged on fresh rows) to the
# `source` value as it appears in the user-supplied existing-locations CSV.
# Note the deliberate asymmetry for OSM: fresh rows are tagged "osm",
# the cache file uses "openstreetmap".
_SERVICES: dict[str, Callable] = {
    "googlemaps": get_installation_coordinates_google,
    "geoapify": get_installation_coordinates_geoapify,
    "osm": get_installation_coordinates_osm,
}
_EXISTING_SOURCE_BY_SERVICE = {
    "googlemaps": "googlemaps",
    "geoapify": "geoapify",
    "osm": "openstreetmap",
}

# Activity types skipped entirely (no address worth geocoding):
# 10 = aircraft, 50 = shipping.
_SKIP_ACTIVITY_TYPES = (10.0, 50.0, pd.NA)
_EXISTING_REQUIRED_COLS = ("installation_id", "source")


class ExtractInstallationLocationsPipeline(Pipeline):
    """Geocode installation addresses via the configured services, in parallel.

    Inputs:
        Extracted installations parquet at
        `settings.fp("installations", settings.dir_extracted, ending="parquet")`,
        plus an optional user-supplied existing-locations CSV at
        `settings.fp_manual("existing_installation_locations")`. When the
        CSV is registered in `Settings.manual_files`, rows whose `source`
        matches a configured service's expected source value suppress API
        calls *for that service* on those `installation_id`s. Required
        columns in the CSV: `installation_id`, `source`.

    Output:
        One cohesive locations table per installation/service combination.
        Composition:

        - For each service key in `api_keys`: existing rows matching that
          service's source value pass through verbatim, **plus** freshly-
          fetched rows for `installation_id`s not yet present for that
          service (tagged `source=<service_key>`).
        - Existing rows whose `source` does **not** map to any configured
          service are dropped — the output mirrors what the API loop would
          have produced.

    Output location:
        `settings.fp("installation_locations", settings.dir_extracted,
        ending="parquet")`

    Failure modes (`ValueError`):

    - `api_keys` is empty.
    - A key in `api_keys` is not one of `_SERVICES`.
    - Existing-locations CSV is registered but missing
      `installation_id` or `source` columns.
    """

    name = "extract_installation_locations"

    def __init__(
        self,
        settings: Settings,
        api_keys: dict[str, str],
        max_installations: int | None = None,
    ):
        super().__init__(settings)
        if not api_keys:
            raise ValueError("api_keys is empty — nothing to fetch.")
        unknown = set(api_keys) - set(_SERVICES)
        if unknown:
            raise ValueError(
                f"Unknown geocoding services in api_keys: {sorted(unknown)}. "
                f"Valid keys: {sorted(_SERVICES)}."
            )
        self.api_keys = api_keys
        self.max_installations = max_installations

    def load(self) -> None:
        # Installations — required.
        df_inst = pd.read_parquet(
            self.settings.fp(
                "installations", self.settings.dir_extracted, ending="parquet"
            )
        )
        df_inst = df_inst[~df_inst["activity_type_code"].isin(_SKIP_ACTIVITY_TYPES)]
        if self.max_installations is not None:
            df_inst = df_inst.head(self.max_installations)
        self.df_installations = df_inst

        # Existing locations — optional.
        try:
            existing_path = self.settings.fp_manual("existing_installation_locations")
        except KeyError:
            self.df_existing = None
            return
        df_existing = pd.read_csv(existing_path, parse_dates=["created_at"])
        missing = [c for c in _EXISTING_REQUIRED_COLS if c not in df_existing.columns]
        if missing:
            raise ValueError(
                f"Existing-locations CSV at {existing_path} is missing required "
                f"columns: {missing}. Found: {list(df_existing.columns)}."
            )
        self.df_existing = df_existing

    def transform(self) -> None:
        frames: list[pd.DataFrame] = []

        # 1) Pass-through existing rows for configured services only.
        if self.df_existing is not None:
            for service in self.api_keys:
                expected_source = _EXISTING_SOURCE_BY_SERVICE[service]
                rows = self.df_existing[self.df_existing["source"] == expected_source]
                if not rows.empty:
                    frames.append(rows.copy())

        # 2) Fresh fetches in parallel — per-service skip of already-cached IDs.
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(self.api_keys)
        ) as executor:
            future_to_service: dict[concurrent.futures.Future, str] = {}
            for service, api_key in self.api_keys.items():
                if not api_key:
                    logger.warning(
                        f"API key / user-agent for {service} is falsy — skipping."
                    )
                    continue
                df_to_fetch = self._installations_to_fetch(service)
                if df_to_fetch.empty:
                    logger.info(f"All installations already cached for {service}.")
                    continue
                future = executor.submit(_SERVICES[service], df_to_fetch, api_key)
                future_to_service[future] = service

            for future in concurrent.futures.as_completed(future_to_service):
                service = future_to_service[future]
                try:
                    df_result = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"Service {service} raised: {exc}")
                    continue
                if df_result is None or df_result.empty:
                    continue
                frames.append(df_result.assign(source=service))
                logger.info(f"Fetched {len(df_result)} rows from {service}.")

        if not frames:
            raise ValueError("No locations produced — nothing to save.")
        self.df = pd.concat(frames, ignore_index=True)

    def save(self) -> None:
        self.df.to_parquet(
            self.settings.fp(
                "installation_locations",
                self.settings.dir_extracted,
                ending="parquet",
            ),
            index=False,
        )

    def _installations_to_fetch(self, service: str) -> pd.DataFrame:
        """Return installations needing a fresh API call for `service`."""
        if self.df_existing is None:
            return self.df_installations
        expected_source = _EXISTING_SOURCE_BY_SERVICE[service]
        cached_ids = set(
            self.df_existing.loc[
                self.df_existing["source"] == expected_source, "installation_id"
            ]
        )
        return self.df_installations[
            ~self.df_installations["installation_id"].isin(cached_ids)
        ]


class InstallationLocationsBundle(Bundle):
    """Installation locations: geocode addresses via configured services.

    Source-level runtime config:

    - `api_keys` — `dict[str, str]` mapping service key to API key (or
      user-agent string for OSM). Service keys must be a subset of
      `_SERVICES` (`googlemaps`, `geoapify`, `osm`).
    - `max_installations` — optional test cap, applied after the
      activity-type filter.

    Existing-locations cache (optional): register the path via
    `Settings(manual_files={"existing_installation_locations": Path(...)})`.
    When present, suppresses API calls for `installation_id`s already
    cached for that service (per-service skip — a cached OSM row only
    suppresses OSM, not Geoapify or Googlemaps).
    """

    name = "installation_locations"

    def __init__(
        self,
        settings: Settings,
        api_keys: dict[str, str],
        max_installations: int | None = None,
    ):
        self.api_keys = api_keys
        self.max_installations = max_installations
        super().__init__(settings)

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            ExtractInstallationLocationsPipeline(
                self.settings,
                api_keys=self.api_keys,
                max_installations=self.max_installations,
            ),
        ]
