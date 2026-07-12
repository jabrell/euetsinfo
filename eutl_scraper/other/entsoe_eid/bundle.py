"""Pipeline for extracting the mapping from installations to ENTSOE power plants
and facilities under the Industrial Emissions Directive (IED).

As the data are already organized according to the data schema, the pipeline
simply reads the given file and writes it to the extracted directory.

"""

import zipfile
from pathlib import Path

import pandas as pd
from loguru import logger

from eutl_scraper.pipeline import Bundle, Pipeline
from eutl_scraper.settings import Settings

MY_DIR = Path(__file__).resolve().parent
ZIP_DATA = MY_DIR / "plant_eid_mapping.zip"


class ExtractENTSOEPipeline(Pipeline):
    """Extract the mapping from EUTL installations to ENTSOE power plants.

    Inputs:
        Zip file containing the mapping files as csv: (constants `ZIP_DATA`)

    Output:
        Three tables written to `dir_extracted`:

        - **powerplants**: one row per power plant with `plant_id` and the respective
            `fuel`
        - **map_entsoe_to_plant**: mapping from ENTSOE power plants to the established
            power plants: `eic_g`, `name_g`, `eic_p`, `name_p`, `plant_id`
        - **map_installation_to_plant**: mapping from EUTL installations to the plants:
            `installation_id`, `plant_id`

    Output locations (`ending="parquet"`):

    - `settings.fp("powerplants", settings.dir_extracted, ...)`
    - `settings.fp("map_entsoe_to_plant", settings.dir_extracted, ...)`
    - `settings.fp("map_installation_to_plant", settings.dir_extracted, ...)`
    """

    name = "extract_entsoe_mapping"

    def __init__(self, settings: Settings):
        super().__init__(settings)

    def load(self) -> None:
        pass

    def transform(self) -> None:
        pass

    def save(self) -> None:
        source_files = {
            "powerplants": "plants_final.csv",
            "map_entsoe_to_plant": "entsoe_2_plants_final.csv",
            "map_installation_to_plant": "eutl_2_plants_final.csv",
        }
        with zipfile.ZipFile(ZIP_DATA, "r") as zf:
            for key, filename in source_files.items():
                fn_out = self.settings.fp(
                    key, self.settings.dir_extracted, ending="parquet"
                )
                logger.info(f"[{self.name}] writing {key} to {fn_out}")
                with zf.open(filename) as f:
                    pd.read_csv(f).to_parquet(fn_out)


class ExtractEIDPipeline(Pipeline):
    """Extract the mapping from EUTL installations to EID facilities.

    Inputs:
        Zip file containing the mapping files as csv: (constants `ZIP_DATA`)

    Output:
        One table written to `dir_extracted`:

        - **map_installation_to_eid_facility**: one row per installation
            with the respective EID facility: `installation_id`, `facility_inspire_id",
            `match_probability`

    Output locations (`ending="parquet"`):

    - `settings.fp("map_installation_to_eid_facility", settings.dir_extracted, ...)`
    """

    name = "extract_eid_mapping"

    def __init__(self, settings: Settings):
        super().__init__(settings)

    def load(self) -> None:
        pass

    def transform(self) -> None:
        pass

    def save(self) -> None:
        source_files = {
            "map_installation_to_eid_facility": "eutl_2_iep_final.csv",
        }
        with zipfile.ZipFile(ZIP_DATA, "r") as zf:
            for key, filename in source_files.items():
                fn_out = self.settings.fp(
                    key, self.settings.dir_extracted, ending="parquet"
                )
                logger.info(f"[{self.name}] writing {key} to {fn_out}")
                with zf.open(filename) as f:
                    pd.read_csv(f).to_parquet(fn_out)


class EntsoeEidBundle(Bundle):
    """Extract the mapping from EUTL installations to ENTSOE power plants and
    IED facilities."""

    name = "entsoe_eid_mapping"

    def __init__(self, settings: Settings):
        super().__init__(settings)

    def _build_pipelines(self) -> list[Pipeline]:
        return [
            ExtractENTSOEPipeline(self.settings),
            ExtractEIDPipeline(self.settings),
        ]
