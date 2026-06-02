# Data

The data processed by the routines provided are all open source data. The major
aim is to make the data for emissions trading easily accessible and to enrich them
to make them more usable. The sources used are:

| Reference | Description | Remarks |
| --- | --- | --- |
| https://union-registry-data.ec.europa.eu/report/welcome | The Union Registry page provides data on installations and compliance of units regulated under the EUETS together with allowance transactions. It also provides information on transactions under the Effort Sharing desicion | |
| https://www.geoapify.com/ | Installation coordinates are obtained using reverse geocoding with Geoapify. Roberto Rossini from Bruegel provided a draft version of the code. As second version exists for coordinates from Google maps. But these are not distributed. | |
| https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download | Prices and volumes including revenues by EU member state. Thomas Mramor from Bruegel provided a draft version of the code. | |
| Leakage Lists | Used for NACE codes at the installation level. These files used to be available for download but have been removed at some point in time. We saved the original files available in the code (eutl_scraper/other/nace_codes). | |



