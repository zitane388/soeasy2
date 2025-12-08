# scrapers/scraper_factory.py
from urllib.parse import urlparse
from scrapers.uniqlo.jp_scraper import UniqloJPScraper
from scrapers.uniqlo.vn_scraper import UniqloVNScraper

class ScraperFactory:

    def get_scraper(self, url: str):
        host = urlparse(url).netloc.lower()
        path = urlparse(url).path.lower()

        if "uniqlo.com" in host:
            if "/jp/" in path:
                return UniqloJPScraper()
            if "/vn/" in path or "/en/" in path:
                return UniqloVNScraper()

        return None
