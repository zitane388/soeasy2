# scrapers/scraper_factory.py
from urllib.parse import urlparse
from scrapers.product_pages.uniqlo.jp_scraper import UniqloJPScraper
from scrapers.product_pages.uniqlo.vn_scraper import UniqloVNScraper
from scrapers.product_pages.gu.jp_scraper import GuJPScraper
from scrapers.product_pages.muji.jp_scraper import MujiJPScraper

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

        return None
