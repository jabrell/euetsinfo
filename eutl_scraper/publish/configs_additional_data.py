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
            ],
        )
    )
    column_mapping: dict[str, str] = field(
        default_factory=lambda: {
            "installation_id": "installation_id",
            "lat": "latitude",
            "lon": "longitude",
        }
    )

    def __post_init__(self):
        self.transformers = [
            self._dropna_subset(["lat", "lon"]),
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
        }
    )

    def __post_init__(self):
        self.type_convertors = {
            "nace_2015": self._float_to_nace("nace_2015"),
            "nace_2020": self._float_to_nace("nace_2020"),
        }

        self.transformers = [
            self._drop_duplicates_subset(["installation_id"]),
        ]
