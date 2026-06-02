# EUETS.INFO

The European Union Emissions Trading System (EU ETS) is a centerpiece of European climate policy, regulating greenhouse gas emissions for energy generation, energy-intensive industries, and aviation. As the world's largest carbon market, the system's administrative backbone is the European Union Transaction Log (EUTL). The EUTL records all allowance transactions, including those under the EU ETS, the Effort Sharing Decision (ESD), and the upcoming ETS2 for transport and buildings.

While the EUTL provides comprehensive registry data, accessing and analyzing this raw information can be technically challenging. To increase market transparency and facilitate empirical research on trading and compliance behavior, this repository extracts, cleans, and structures EUTL data into a standardized data model.

Additionally, the repository integrates associated metadata, such as facility locations and cross-references to external datasets like ENTSO-E power plants, providing a richer context for analysis.

Following open science and FAIR data principles, the complete processed dataset is distributed as a [Frictionless](https://frictionlessdata.io/) data package. This ensures that both the data and the open-source routines used to process it remain highly accessible and interoperable for researchers and analysts.

!!! warning "Under Active Development"
    This repository is currently in the development stage. Features, APIs, and overall architecture are subject to breaking changes without prior notice.

## Acknowledgements

This project originally began as a webpage, euets.info, to make the data more accessible to the public. With the creation of this repository, I have decided to stop maintaining the website. Fortunately, Bruegel now provides an excellent alternative with their Carbon Tracker, which is a fantastic tool for visualizing and exploring the data.

This project has greatly benefited from many ongoing discussions and contributions. I want to particularly thank Mirjam Kosch and Leonhard Stimpfle for their input. I am also grateful to Hannes Weigt and the University of Basel for providing the time and freedom to work on this project. Roberto Rossini provided input to the reverse geocoding for the EUETS installations. Thomas Mramor made the first version of the pipeline for the EEX auction data.

Over the years, the project received financial support from:

- [Bruegel](https://www.bruegel.org/)
- [European University Institute,Florence School of Regulation – Climate](https://fsr.eui.eu/energy/climate/) under the "LIFE COASE - Collaborative Observatory for ASsessment of the EU ETS" project (Grant Agreement n. LIFE21-GIC-IT-LIFE COASE - 101074420)