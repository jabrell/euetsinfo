# EUETS.INFO

The European Union Emissions Trading System (EU ETS) is a centerpiece of European climate policy, regulating greenhouse gas emissions for energy generation, energy-intensive industries, and aviation. As the world's largest carbon market, the system's administrative backbone is the European Union Transaction Log (EUTL). The EUTL records all allowance transactions, including those under the EU ETS, the Effort Sharing Decision (ESD), and the upcoming ETS2 for transport and buildings.

While the EUTL provides comprehensive registry data, accessing and analyzing this raw information can be technically challenging. To increase market transparency and facilitate empirical research on trading and compliance behavior, this repository extracts, cleans, and structures EUTL data into a standardized data model.

Additionally, the repository integrates associated metadata, such as facility locations and cross-references to external datasets like ENTSO-E power plants, providing a richer context for analysis.

Following open science and FAIR data principles, the complete processed dataset is distributed as a [Frictionless](https://frictionlessdata.io/) data package. This ensures that both the data and the open-source routines used to process it remain highly accessible and interoperable for researchers and analysts.

If you're interested in the data produced by this repository, you can access them
interactively using the [Bruegel ETS Tracker](https://ets.bruegel.org/). The source
data can be downloaded from [Zenodo](https://doi.org/10.5281/zenodo.20509230)
(this link always points to the latest release).

## Releases

All releases are published on Zenodo. Earlier versions remain available for
reproducibility; newest release first.

| Version | Published | Zenodo | Changes |
| --- | --- | --- | --- |
| 4 | 2026-11-06 | [10.5281/zenodo.24013118](https://doi.org/10.5281/zenodo.24013118) | Update to the current EUTL data. The EUTL files are now located at runtime through the download listing of the Union Registry website; the provider had moved them, and the previously used addresses kept serving outdated copies. ETS2: the regulated entities of the ETS2 (activity type code 70, 1,184 entities) are now part of the installations table, including their accounts, and are tagged with `ets_id` `ets2` (previously the few already listed were tagged `euets`). The placeholder installations previously derived from the compliance data for the member states' ETS2 accounts (`ets_id` `ETS2`, no account) are dropped, as they no longer appear in the source data. Installation locations: 609 manually curated coordinates provided by Bruegel are added as a separate source (`manual_bruegel`), and about 1,300 newly listed installations are geocoded. ETS2 regulated entities are fuel suppliers rather than plants, so their locations mark the registered company address, not an emission source. |
| 3 | 2026-10-07 | [10.5281/zenodo.23208374](https://doi.org/10.5281/zenodo.23208374) | Update for the 2026 release of EUTL data. Fix: transaction parties held in the EU registry (registry name `Eu`) now get registry id `EU` and a valid account id; previously these were missing, and 24 accounts appeared twice in the accounts table (with and without registry id). Fix: projects issuing temporary CERs now have project type `tCER` (previously `CER`). |
| 2 | 2026-07-17 | [10.5281/zenodo.21414185](https://doi.org/10.5281/zenodo.21414185) | Added links to ENTSO-E power plants and to industrial facilities reporting under the Industrial Emission Directive. |
| 1 | 2026-06-02 | [10.5281/zenodo.20509231](https://doi.org/10.5281/zenodo.20509231) | Initial release. |

## Which data are processed

We process data from several sources. For a detailed explanation of data and how
they are processed see the data section.

The **main data** provided are:

| Data | Reference | Remarks |
| --- | --- | --- |
| Data on emissions and transactions under the EUTS | [https://union-registry-data.ec.europa.eu/report/welcome](https://union-registry-data.ec.europa.eu/report/welcome) | |
| Location of stationary installations  regulated under the EUETS| [https://www.geoapify.com/](https://www.geoapify.com/) | |
| NACE codes for EUETS installations | Based on the leakage lists formerly provided by the EU Commission | |
|Prices and volumes including revenues by EU member state. Thomas Mramor from Bruegel provided a draft version of the code. |  [https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download](https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download) | Due to license restrictions these data are not provided fro download but the routine to download and process the data is available. |

Furthermore **linking tables** to relate the EUTL data to other datasets are provided:


| Data | Reference | Remarks |
| --- | --- | --- |
| Mapping to  [ENTSOE power plants](https://transparency.entsoe.eu/)| [Abrell, Kosch, and Stimpfle (2025), *Linking EU ETS installations to ENTSO-E Power Plants and IEP Facilities*.](./static/abrell_kosch_stimpfle_2025_linking_euets_entsoe_iep.pdf)| |
| Mapping to facilities regulated under the [Industrial Emission Directive](https://industry.eea.europa.eu/) (local air pollution) | [Abrell, Kosch, and Stimpfle (2025), *Linking EU ETS installations to ENTSO-E Power Plants and IEP Facilities*.](./static/abrell_kosch_stimpfle_2025_linking_euets_entsoe_iep.pdf) | |
|  Mapping from EUETS company registration numbers to the ORBIS identifiers. | [Cameron, A. & Ho, V. (2024): Matching the EU Transaction Log and ORBIS:  A Natural Language Processing approach.](https://single-market-economy.ec.europa.eu/single-market/chief-economist-business-intelligence-unit/analytical-work/single-market-industry-and-competitiveness/matching-eu-transaction-log-orbis-database_en)|

## Acknowledgements

This project originally began as a webpage, euets.info, to make the data more accessible to the public. With the creation of this repository, I have decided to stop maintaining the website. Fortunately, Bruegel now provides an excellent alternative with their [Carbon Tracker](https://ets.bruegel.org/), which is a fantastic tool for visualizing and exploring the data.

This project has greatly benefited from many ongoing discussions and contributions. I want to particularly thank Mirjam Kosch and Leonhard Stimpfle for their input. I am also grateful to Hannes Weigt and the University of Basel for providing the time and freedom to work on this project. Roberto Rossini provided input to the reverse geocoding for the EUETS installations. Thomas Mramor made the first version of the pipeline for the EEX auction data.

The project received financial support from:

- [Bruegel](https://www.bruegel.org/) (ongoing)
- [European University Institute,Florence School of Regulation – Climate](https://fsr.eui.eu/energy/climate/) under the "LIFE COASE - Collaborative Observatory for ASsessment of the EU ETS" project (Grant Agreement n. LIFE21-GIC-IT-LIFE COASE - 101074420)