# Data

The routines in this project collect open data on the EU Emissions Trading
System (EU ETS) from the EU Transaction Log (EUTL) and a few related sources,
clean them, and republish them in an easily accessible and enriched form. This
page introduces *what the data describe* and *what we can observe*; the
[Data Model](data_model.md) documents the resulting tables, and the
[Data Processing](processing/eutl.md) section explains how they are built.

## How the EU Transaction Log is structured

The EUTL is the administrative engine of the EU ETS (and ETS2). Its data are best
understood as three connected layers, bridging the physical world of emissions
and the legal world of the companies that cause them:

- **Physical layer — emissions.** *Installations* are the regulated entities;
  all emission accounting happens strictly at this level. Each year an
  installation must surrender allowances equal to its verified emissions.
- **Transaction layer — allowance transactions.** Allowances are never
  transferred between installations directly, only between *accounts*. Every
  installation is represented by an **Operator Holding Account (OHA)**;
  non-regulated actors such as financial intermediaries trade through
  **Person Holding Accounts (PHA)**; regulatory authorities issue allocations and
  receive surrendered allowances through **Administrative Accounts (AA)**.
- **Ownership layer — persons.** The real-world companies and bodies behind the
  accounts are not represented directly in the EUTL. Each account instead names
  an **Account Holder**, the bridge that links external legal entities to their
  accounts inside the system.

![Three-layer structure of the EU Transaction Log: account holders in the
ownership layer, the operator-, person-holding and administrative accounts in the
transaction layer, and installations in the physical layer.](../figures/data_model_simple.svg)

## What we observe

Across these layers the EUTL lets us observe a specific set of entities and
fields. Installations carry their identity and a yearly **compliance** record
(verified emissions, allocated and surrendered allowances); accounts carry their
identity and the **transactions** moving allowances between them; and account
holders carry the identifying details of the legal entity behind each account.

![Data observable per entity: account holders (name, address, company
registration number), accounts (name, holder, type), transactions (date,
accounts, amount by unit type), installations (name, address, activity type) and
their yearly compliance (verified emissions, allocated and surrendered
allowances).](../figures/data_model_tables.svg)

These observable entities map directly onto the published tables described in the
[Data Model](data_model.md). Several of them — account holders, projects, and
installation locations among others — are not provided ready-made by the EUTL but
*derived* during processing; see [Data Processing](processing/eutl.md) for the
details.

## Sources

All processed data are open data. The sources used are:

| Reference | Description | Remarks |
| --- | --- | --- |
| [https://union-registry-data.ec.europa.eu/report/welcome](https://union-registry-data.ec.europa.eu/report/welcome) | The Union Registry page provides data on installations and compliance of units regulated under the EUETS together with allowance transactions. It also provides information on transactions under the Effort Sharing  decision | |
| [https://www.geoapify.com/](https://www.geoapify.com/) | Installation coordinates are obtained using reverse geocoding with Geoapify. Roberto Rossini from Bruegel provided a draft version of the code. As second version exists for coordinates from Google maps. But these are not distributed. | |
| [https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download](https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download) | Prices and volumes including revenues by EU member state. Thomas Mramor from Bruegel provided a draft version of the code. | |
| Leakage Lists | Used for NACE codes at the installation level. These files used to be available for download but have been removed at some point in time. We saved the original files available in the code (eutl_scraper/other/nace_codes). | |
| [https://transparency.entsoe.eu/](https://transparency.entsoe.eu/) | ENTSO-E Transparency Platform. Provides the power plant (generation and production unit) data that EUTL installations are mapped onto. | |
| [https://industry.eea.europa.eu/](https://industry.eea.europa.eu/) | Industrial Emissions Portal (IEP). Provides the industrial facilities, regulated under the Industrial Emissions Directive (IED), that EUTL installations are mapped onto. | |
| [Abrell, Kosch, and Stimpfle (2025)](../static/abrell_kosch_stimpfle_2025_linking_euets_entsoe_iep.pdf) | Abrell, J., Kosch, M., and Stimpfle, L. (2025), *Linking EU ETS installations to ENTSO-E Power Plants and IEP Facilities*. Describes the methodology used to establish the mapping from EUTL installations to ENTSO-E power plants and IEP facilities. [Download PDF](../static/abrell_kosch_stimpfle_2025_linking_euets_entsoe_iep.pdf). | |
