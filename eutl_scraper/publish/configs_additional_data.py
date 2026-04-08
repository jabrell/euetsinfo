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
