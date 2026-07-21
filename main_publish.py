from datetime import date
from pathlib import Path

from eutl_scraper import Settings
from eutl_scraper.logger import setup_logging
from eutl_scraper.publish import publish_data_package

if __name__ == "__main__":
    settings = Settings(dir_data="data_tmp/")
    fn_publish = Path("published") / f"eutl_data_package_{date.today().isoformat()}.zip"
    setup_logging("INFO")
    package, report = publish_data_package(
        settings=settings,
        fn_out=fn_publish,
        validate_package=True,
        include_eex_auctions=False,
    )
    print("here")
