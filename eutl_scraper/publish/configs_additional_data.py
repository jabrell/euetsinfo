from dataclasses import dataclass, field
from pathlib import Path

from .configs import SCHEMA_PATH, BaseConfig, ResourceMetadata


@dataclass
class InstallationLocations(BaseConfig):
    name: str = "installation_locations"
    schema_path: Path = SCHEMA_PATH / "installation_locations.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS Installation Locations",
            description=(
                "Locations of installations in the European Union Emissions "
                "Trading System (EU ETS)."
            ),
            sources=[
                {
                    "title": "European Commission, EUTL database",
                    "path": "https://union-registry-data.ec.europa.eu/report/welcome",
                },
                {
                    "title": "GEOAPIFY API",
                    "path": "https://api.geoapify.com",
                },
                {
                    "title": "Google Maps Geocoding API",
                    "path": "https://developers.google.com/maps/documentation/geocoding/overview",
                },
            ],
        )
    )
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
    name: str = "nace_mappings"
    schema_path: Path = SCHEMA_PATH / "nace_mappings.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EU ETS NACE Mapping",
            description=(
                "Mapping of NACE codes for installations in the European Union "
                "Emissions Trading System (EU ETS)."
            ),
            sources=[
                {
                    "title": "NACE Rev. 2 classification, Eurostat",
                    "path": "https://ec.europa.eu/eurostat/web/nace/",
                },
            ],
        )
    )
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
            "nace_2015": self._float_to_nace("nace_2015"),
            "nace_2020": self._float_to_nace("nace_2020"),
            "created_at": self._to_datetime("created_at"),
        }

        self.transformers = [
            self._drop_duplicates_subset(["installation_id"]),
        ]


@dataclass
class EEXAuctions(BaseConfig):
    name: str = "eex_auctions"
    schema_path: Path = SCHEMA_PATH / "eex_auctions.yaml"
    resource_metadata: ResourceMetadata = field(
        default_factory=lambda: ResourceMetadata(
            title="EEX Auction Data",
            description=(
                "Data on auctions of emission allowances on the European Energy "
                "Exchange (EEX)."
            ),
            sources=[
                {
                    "title": "European Energy Exchange (EEX)",
                    "path": "https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download",
                },
            ],
        )
    )
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
