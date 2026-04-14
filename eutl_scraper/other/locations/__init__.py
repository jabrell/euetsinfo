"""Module to fetch coordinates for EUTL installations based on the
[Geoapify API](https://www.geoapify.com/).

The first version of this module was provided by: Roberto Rossini (Bruegel)"""

from .fetch_coordinates import geocode_installations, load_installations
from .pipeline import pipeline_installation_coordinates

__all__ = [
    "geocode_installations",
    "load_installations",
    "pipeline_installation_coordinates",
]
