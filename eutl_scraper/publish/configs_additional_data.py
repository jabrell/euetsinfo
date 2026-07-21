"""Publication configurations for non-EUTL auxiliary tables.

These tables are produced by bundles outside `EUTLBundle`:

- `InstallationLocations` — coordinates from `InstallationLocationsBundle`.
- `NaceMappings` — NACE codes from `NaceFromLeakageListsBundle`.
- `EEXAuctions` — EUA primary auction results from `EEXAuctionsBundle`.

They share the `BaseConfig` structure defined in `configs` and are
registered alongside the EUTL configs in `table_registry`.
"""

from dataclasses import dataclass, field
from pathlib import Path

from .configs import SCHEMA_PATH, BaseConfig


@dataclass
class InstallationLocations(BaseConfig):
    """Publication config for the `installation_locations` table.

    Geocoded latitude/longitude for installations. Rows with missing
    coordinates are dropped by the configured transformer.
    """

    name: str = "installation_locations"
    schema_path: Path = SCHEMA_PATH / "installation_locations.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "latitude": "latitude",
            "longitude": "longitude",
            "source": "source",
            "created_at": "created_at",
        }
    )

    def __post_init__(self):
        self.type_convertors = {
            "created_at": self._to_datetime("created_at"),
        }
        self.transformers = [
            self._dropna_subset(["latitude", "longitude"]),
        ]


@dataclass
class NaceMappings(BaseConfig):
    """Publication config for the `nace_mappings` table.

    Maps installations to their NACE Rev. 2 economic activity codes from
    the 2015 and 2020 carbon leakage lists. Duplicate `installation_id`
    rows are dropped by the configured transformer.
    """

    name: str = "nace_mappings"
    schema_path: Path = SCHEMA_PATH / "nace_mappings.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "nace_2015": "nace_2015",
            "nace_2020": "nace_2020",
            "created_at": "created_at",
        }
    )

    def __post_init__(self):
        self.type_convertors = {
            "nace_2015": self._format_nace("nace_2015"),
            "nace_2020": self._format_nace("nace_2020"),
            "created_at": self._to_datetime("created_at"),
        }

        self.transformers = [
            self._drop_duplicates_subset(["installation_id"]),
        ]


@dataclass
class EEXAuctions(BaseConfig):
    """Publication config for the `eex_auctions` table.

    EUA primary auction results from the European Energy Exchange:
    auction-level prices, volumes, bidder statistics, and per-country
    revenue allocations.
    """

    name: str = "eex_auctions"
    schema_path: Path = SCHEMA_PATH / "eex_auctions.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "auction_name": "auction_name",
            "auction_price_eur_per_tco2": "auction_price_eur_per_tco2",
            "auction_volume_tco2": "auction_volume_tco2",
            "average_bid_size": "average_bid_size",
            "average_bids_per_bidder": "average_bids_per_bidder",
            "average_volume_bid_per_bidder": "average_volume_bid_per_bidder",
            "average_volume_won_per_bidder": "average_volume_won_per_bidder",
            "contract": "contract",
            "country": "country",
            "cover_ratio": "cover_ratio",
            "date": "date",
            "maximum_bid_eur_per_tco2": "maximum_bid_eur_per_tco2",
            "mean_price_eur_per_tco2": "mean_price_eur_per_tco2",
            "median_price_eur_per_tco2": "median_price_eur_per_tco2",
            "minimum_bid_eur_per_tco2": "minimum_bid_eur_per_tco2",
            "number_of_bids_submitted": "number_of_bids_submitted",
            "number_of_successful_bidders": "number_of_successful_bidders",
            "number_of_successful_bids": "number_of_successful_bids",
            "revenue_at_eur": "revenue_at_eur",
            "revenue_be_eur": "revenue_be_eur",
            "revenue_bg_eur": "revenue_bg_eur",
            "revenue_cy_eur": "revenue_cy_eur",
            "revenue_cz_eur": "revenue_cz_eur",
            "revenue_de_eur": "revenue_de_eur",
            "revenue_dk_eur": "revenue_dk_eur",
            "revenue_ee_eur": "revenue_ee_eur",
            "revenue_el_eur": "revenue_el_eur",
            "revenue_es_eur": "revenue_es_eur",
            "revenue_fi_eur": "revenue_fi_eur",
            "revenue_fr_eur": "revenue_fr_eur",
            "revenue_hr_eur": "revenue_hr_eur",
            "revenue_hu_eur": "revenue_hu_eur",
            "revenue_ie_eur": "revenue_ie_eur",
            "revenue_innovation_fund_eur": "revenue_innovation_fund_eur",
            "revenue_innovation_fund_rrf_eur": "revenue_innovation_fund_rrf_eur",
            "revenue_is_eur": "revenue_is_eur",
            "revenue_it_eur": "revenue_it_eur",
            "revenue_li_eur": "revenue_li_eur",
            "revenue_lt_eur": "revenue_lt_eur",
            "revenue_lu_eur": "revenue_lu_eur",
            "revenue_lv_eur": "revenue_lv_eur",
            "revenue_modernisation_fund_eur": "revenue_modernisation_fund_eur",
            "revenue_ms_rrf_eur": "revenue_ms_rrf_eur",
            "revenue_mt_eur": "revenue_mt_eur",
            "revenue_nl_eur": "revenue_nl_eur",
            "revenue_no_eur": "revenue_no_eur",
            "revenue_pl_eur": "revenue_pl_eur",
            "revenue_pt_eur": "revenue_pt_eur",
            "revenue_ro_eur": "revenue_ro_eur",
            "revenue_se_eur": "revenue_se_eur",
            "revenue_si_eur": "revenue_si_eur",
            "revenue_sk_eur": "revenue_sk_eur",
            "revenue_social_climate_fund_eur": "revenue_social_climate_fund_eur",
            "standard_deviation_bid_volume_per_bidder": (
                "standard_deviation_bid_volume_per_bidder"
            ),
            "standard_deviation_volume_won_per_bidder": (
                "standard_deviation_volume_won_per_bidder"
            ),
            "status": "status",
            "time": "time",
            "total_amount_of_bids": "total_amount_of_bids",
            "total_number_of_bidders": "total_number_of_bidders",
            "total_revenue_eur": "total_revenue_eur",
            "datetime": "datetime",
            "created_at": "created_at",
        }
    )

    def __post_init__(self):
        self.type_convertors = {
            "date": self._to_datetime("date"),
            "datetime": self._to_datetime("datetime"),
            "created_at": self._to_datetime("created_at"),
        }


@dataclass
class Powerplants(BaseConfig):
    """Publication config for the `powerplants` table.

    Power plant data from the ENTSO-E Transparency Platform.
    """

    name: str = "powerplants"
    schema_path: Path = SCHEMA_PATH / "powerplants.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {"plant_id": "plant_id", "fuel": "fuel"}
    )


@dataclass
class MapInstallationToPlant(BaseConfig):
    name: str = "map_installation_to_plant"
    schema_path: Path = SCHEMA_PATH / "map_installation_to_plant.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "plant_id": "plant_id",
        }
    )

    def __post_init__(self):
        self.type_convertors = {}


@dataclass
class MapInstallationToEidFacility(BaseConfig):
    name: str = "map_installation_to_eid_facility"
    schema_path: Path = SCHEMA_PATH / "map_installation_to_eid_facility.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "facility_inspire_id": "facility_inspire_id",
            "match_probability": "match_probability",
        }
    )


@dataclass
class MapEntsoeToPlant(BaseConfig):
    name: str = "map_entsoe_to_plant"
    schema_path: Path = SCHEMA_PATH / "map_entsoe_to_plant.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "eic_g": "eic_g",
            "name_g": "name_g",
            "eic_p": "eic_p",
            "name_p": "name_p",
            "plant_id": "plant_id",
        }
    )


@dataclass
class MapOrbis(BaseConfig):
    name: str = "map_orbis"
    schema_path: Path = SCHEMA_PATH / "map_orbis.yaml"
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "account_holder_id": "account_holder_id",
            "orbis_bvd_id": "orbis_bvd_id",
            "source": "source",
            "rank": "rank",
        }
    )

    def __post_init__(self):
        self.type_convertors = {
            "rank": self._to_nullable_int("rank"),
            "created_at": self._to_datetime("created_at"),
        }
