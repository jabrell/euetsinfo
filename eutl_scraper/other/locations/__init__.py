"""Module to fetch coordinates for EUTL installations based on the
[Geoapify API](https://www.geoapify.com/).

The first version of this module was provided by: Roberto Rossini (Bruegel)"""

# from .fetch_coordinates import geocode_installations, load_installations
from .bundle import ExtractInstallationLocationsPipeline, InstallationLocationsBundle
from .geoapify_coordinates import get_installation_coordinates_geoapify
from .google_coordinates import get_installation_coordinates_google
from .osm_coordinates import get_installation_coordinates_osm
from .pipeline import load_installations, pipeline_installation_coordinates

__all__ = [
    "load_installations",
    "pipeline_installation_coordinates",
    "get_installation_coordinates_google",
    "get_installation_coordinates_geoapify",
    "get_installation_coordinates_osm",
    "ExtractInstallationLocationsPipeline",
    "InstallationLocationsBundle",
]
