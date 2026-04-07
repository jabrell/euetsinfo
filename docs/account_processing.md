Accounts data are spread across three files:

1. The zip file that can be directly download: [current version](https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/_all_extracts/account/accounts_daily.csv.gz)
2. Download through the [Power-Bi app](https://union-registry-data.ec.europa.eu/report/eu-registry-accounts)
3. Accounts involved in transactions also show up in the [transaction data](https://climate.ec.europa.eu/document/download/0cda99f1-16f6-41e7-b190-887cd71339a4_en?filename=transactions_eutl_2025.zip)

Unfortunately, information is a bit scatter across the three files. The notebook
*analyze_raw_account_data.ipynb* compares the different sources of information.

The approach is to use the direct download (source #1) as basic source. This source,
however, lacks information on the account holders. Holder information and the linking
to accounts is taken mainly from the transaction data (source #3) augmented by
the Power BI data (source #2).

Accounts holders are implicit data in the sense that the EUTL does not provide any
unique identifiers for holders. Collecting the data over time, we need to construct
a stable identifier for holders that is unique. We use a hash-based approach by
constructing unique identifier concatenating the holder name and the company
registration number using it as based for the 10-digit hash.