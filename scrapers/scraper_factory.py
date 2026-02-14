# scrapers/scraper_factory.py
from urllib.parse import urlparse
from scrapers.product_pages.uniqlo.jp_scraper import UniqloJPScraper
from scrapers.product_pages.uniqlo.vn_scraper import UniqloVNScraper
from scrapers.product_pages.gu.jp_scraper import GuJPScraper
from scrapers.product_pages.muji.jp_scraper import MujiJPScraper
from scrapers.product_pages.supersports.jp_scraper import SuperSportsJPScraper
from scrapers.product_pages.lens.lens_scraper import LensScraper

class ScraperFactory:

    def get_scraper(self, url: str):
        host = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower()

        if "uniqlo.com" in host:
            if "/jp/" in path:
                return UniqloJPScraper()
            if "/vn/en/" in path:
                return UniqloVNScraper()
        if "gu-global.com" in host:
            if "/jp/" in path:
                return GuJPScraper()
        if "muji.com" in host:
            if "/jp/" in path:
                return MujiJPScraper()
        if "supersports.com" in host:
            if "/ja-jp/" in path or "/jp/" in path:
                return SuperSportsJPScraper()

        return None

    def get_lens_scraper(self):
        return LensScraper()
