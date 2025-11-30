from urllib.parse import urlparse
from scrapers.uniqlo.jp_scraper import UniqloJPScraper
from scrapers.uniqlo.vn_scraper import UniqloVNScraper


class ScraperFactory:

    def get_scraper(self, url: str):
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.lower()

        if "uniqlo.com" in host:
            if "/jp/" in path:
                return UniqloJPScraper()
            if "/vn/" in path or "/en/" in path:
                return UniqloVNScraper()

        return None
