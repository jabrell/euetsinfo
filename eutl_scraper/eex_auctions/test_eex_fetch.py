import os

from eex_fetch import update_eex_auction_prices

cwd = os.getcwd()

# directory for storing data
data_dir = cwd.replace(os.sep + "eua_scraper", os.sep + "data/source/automatic")

# url for auction price data
eex_url = "https://www.eex.com/en/market-data/market-data-hub/environmentals/eex-eua-primary-auction-spot-download"


prices = update_eex_auction_prices(
    eex_url=eex_url, data_dir=data_dir, download_zip=False
)
