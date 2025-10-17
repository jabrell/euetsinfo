from eutl_scraper.extract import (
    extract_accounts,
    extract_compliance,
    extract_installations,
    extract_transactions,
)

if __name__ == "__main__":
    df_accounts = extract_accounts()
    df_compliance = extract_compliance()
    df_installations = extract_installations()
    df_transactions = extract_transactions()
    print("done")
