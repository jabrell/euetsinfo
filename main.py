from eutl_scraper.extract import extract_accounts, extract_compliance

if __name__ == "__main__":
    df_accounts = extract_accounts()
    df_compliance = extract_compliance()
    print("done")
