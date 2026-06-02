# Data Model

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


