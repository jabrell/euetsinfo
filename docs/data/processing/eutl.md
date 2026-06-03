# EU Transaction Log

This section documents *how* the published data are produced — the sources they
come from, the conventions used to make them join up, and the non-obvious
decisions taken while cleaning them. It complements the [Data Model](../data_model.md),
which describes the *shape* of the resulting tables.

All processing follows the same three stages, regardless of source:

1. **Acquire** — raw files are downloaded (or copied, for manually supplied
   files) into a `source/` directory, untouched.
2. **Extract** — each raw file is read, cleaned, renamed, validated, and written
   as a cleaned table to an `extracted/` directory.
3. **Publish** — the cleaned tables are renamed a second time and packaged as a
   [Frictionless Data Package](https://specs.frictionlessdata.io/).

The bulk of the data comes from the **EU Transaction Log (EUTL)** via the
[Union Registry pages](https://union-registry-data.ec.europa.eu/report/welcome).
A handful of additional sources (installation coordinates, NACE codes, auction
prices) are described under [Other Sources](other.md).

Each entity below is produced by a dedicated pipeline module under
`eutl_scraper/eutl/`. The code is the authoritative reference; the notes here
explain the reasoning and the conventions a data *user* needs to know.

## General approach

### Identifiers

The EUTL itself does not provide globally unique identifiers for accounts or
installations — the same numeric identifier is reused across national
registries. We therefore construct composite identifiers by prefixing the
two-letter registry (country) code:

| Identifier | Construction | Example |
| --- | --- | --- |
| `account_id` | `{registry_code}_{account_identifier}` | `DE_12345` |
| `installation_id` | `{registry_code}_{installation_identifier}` | `DE_98765` |
| `registry_id` | two-letter country code | `DE` |
| `account_holder_id` | SHA-256 of `{holder_name}\|{registration_number}`, truncated to 10 hex digits | `9f2c1a7b04` |

The first three simply prefix the registry code onto the identifier the EUTL
already provides. The `account_holder_id` is different in kind: the EUTL gives
holders **no identifier at all**, so we synthesise a stable one ourselves by
hashing the holder's name together with its company registration number. This is
the only fully self-constructed key in the dataset — see
[Account holders](#account-holders) for the details and trade-offs.

The mapping between registry codes and full registry names lives in
`eutl_scraper/eutl/mappings.py`. Where the raw data only gives the registry
*name* (e.g. in the transaction file), it is mapped back to its code before the
composite identifier is built, so identifiers are consistent across every table.

These identifiers are the primary and foreign keys that link the published
tables together, so they are constructed once, the same way, everywhere.

### ETS1 vs. ETS2

Most data describe the original EU ETS (covering stationary installations and
aviation, here tagged `euets`). The newer **ETS2** (buildings, road transport,
and additional fuels) appears in the compliance data before the installation
register catches up. The `CreateETS2InstallationsPipeline` detects
`installation_id`s that occur in compliance but are missing from the
installations table and creates stub installation rows tagged `ets_id="ETS2"`,
so that every compliance record resolves to an installation. The pipeline
refuses to run if more than 30 installations are missing — a safety check that
flags an upstream change rather than silently mass-tagging rows.

## Accounts

Account information is scattered across three sources, none of which is complete
on its own:

1. The **public daily snapshot** — a gzipped CSV from the EUTL public Azure blob.
   This is the authoritative base for the accounts table.
2. The **PowerBI accounts export** — a manually supplied Excel file. The public
   blob does not expose account-holder identity, so this file is required to
   derive holders (see [Account holders](#account-holders) below).
3. The **transaction file**, which mentions accounts as transaction parties.

The base accounts table is built from source #1 by `ExtractAccountsPipeline`:
strings are stripped, the composite `account_id` is created, columns are
renamed, the account type is unified (combining the `ETS_ACCOUNT_TYPE` and
`FULL_TYPE` fields), and the closure flag is converted to a boolean.

Some accounts appear as parties in the transaction data but never in the public
snapshot (typically older or closed accounts). The
`AddMissingAccountsFromTransactionsPipeline` scans the transaction parties for
such `account_id`s and appends **stub rows** carrying only the limited
information the transaction file provides (account name, type, opening and
closing dates). This ensures every account referenced by a transaction exists in
the accounts table.

## Account holders

Account holders are **not** provided as a distinct entity by the EUTL: the
registry records holder details against each account, but assigns them no stable
identifier, and the same holder recurs across many accounts (and over time, as
snapshots change). To make holders a first-class, linkable entity we have to
*construct* them.

`ExtractAccountHoldersPipeline` (`eutl_scraper/eutl/account_holders.py`) reads
the manually supplied PowerBI Excel and:

- builds a stable `account_holder_id` by hashing the holder's name together with
  its company registration number (a SHA-256 hash truncated to 10 hex digits).
  Using a content hash means the same holder receives the same id on every run
  and across data vintages, without needing a central registry of holders.
  Missing or placeholder registration numbers (blank, all-zeros, dashes) are
  normalised to a sentinel so they hash consistently;
- emits the deduplicated **account_holders** table (one row per unique holder,
  with name, registration number, address, city, LEI, and registry name);
- emits the **link_account_holder** association table mapping each `account_id`
  to its `account_holder_id`, which resolves the many-to-many relationship
  between accounts and holders.

Because the identifier is a hash of name + registration number, two records that
differ only in spelling or formatting will be treated as *different* holders;
conversely, genuinely distinct holders that share both name and registration
number would collide. This is a deliberate, transparent trade-off in favour of
stability and reproducibility.

## Projects

The EUTL has no standalone projects table either — Kyoto-mechanism projects
(those that issued CER, tCER, ERU or RMU credits) are only referenced from the
transactions that move their units. The projects table is therefore *derived*
from the transaction data in the same cleaning pass that produces the
transactions table (`ExtractTransactionsPipeline`,
`eutl_scraper/eutl/transactions.py`).

For each transaction carrying a `project_identifier`, the relevant fields
(originating registry, unit-type description, LULUCF activity, track, expiry
date) are retained; the rows are then deduplicated to one row per project. The
**project type** (`RMU`, `CER`, `tCER`, `ERU`) is inferred from the unit-type
description of the transactions that reference the project. The result is a
compact catalogue of every project ever referenced in the transaction log.
