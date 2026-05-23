# EUTL Scraper v2

The Union Registry is the central register of the EU for installations regulated under
the European Emission Trading system (EU ETS). The EU Transaction Log (EUTL) records the transaction
of allowances under EU emission trading systems mainly the EU ETS but also transactions
under the Effort Sharing Decisions (ESD) and likely under the upcoming ETS2 for
transport and buildings.

This repository collects data from the EUTL, cleans them, and organizes them in
a meaningful data model. Additionally, we collect associated data including locations, links to other data including ENTSOE power plants

The complete data of this package are distributed as a [frictionless](https://frictionlessdata.io/) data package.




## Contributing

### Clone the Repository

```bash
git clone https://github.com/jabrell/eutl_scraper_v2.git
cd eutl_scraper_v2
```

### Installation

This project uses [uv](https://docs.astral.sh/uv/) for fast and reliable Python package management.

First, install uv if you haven't already. Then install the project dependencies (including the
dev dependencies).

```bash
uv sync --all-groups
```
