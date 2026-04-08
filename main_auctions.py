from eutl_scraper import settings
from eutl_scraper.eex_auctions import pipeline_eex_auction_data

if __name__ == "__main__":
    fn_out = settings.DIR_EXTRACTED / "eex_auction_data.csv"
    df_auction = pipeline_eex_auction_data(fn_out=fn_out, download_history=True)
    print("Done downloading and extracting EEX auction data.")
