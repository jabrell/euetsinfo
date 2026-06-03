# Data Model

The data model is structured in a way such that it is easily extensible. The basic
EUTL data are given as several tables that are interconnected by their identifiers.
Many-to-many references are always given with a linking table.

We never merge additional information in the original EUTL data. All additional
information is given in separate as an additional table and the identifiers are
used to link to the EUTL data set. E.g., locations are additional data and thus
not merged into the EUTL data set but kept as a separate table that links to the
installation table using the installation identifier.

The diagram below shows the core published tables and how they relate. To keep
it readable only the key fields (primary and foreign keys) plus a few headline
fields are shown; see the per-table pages under **Tables** for the full column
lists.

<!-- ER_DIAGRAM -->

# Tables

The published dataset is a [Frictionless Data Package](https://specs.frictionlessdata.io/)
made up of several related tables. Each table is described by a Frictionless
*resource descriptor* that records its columns, types, primary key, and the
foreign keys linking it to other tables.

The **Tables** section in the navigation contains a reference page per table,
generated automatically from those descriptors so it always matches the
published data. Each page lists every column with its type and description,
marks the primary
key and foreign-key columns, and summarises how the table relates to the others
(which tables it references and which reference it), along with its upstream
sources.

The two `link_*` tables are association tables that resolve the many-to-many
relationships between installations, accounts, and account holders; the
remaining tables hold the core entities and their compliance, transaction, and
auxiliary data.


