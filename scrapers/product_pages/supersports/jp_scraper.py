from scrapers.base_scraper import BaseScraper


class SuperSportsJPScraper(BaseScraper):
    SITE_KEY = "supersports_jp"

    def request_main(self, url):
        return self._request_html(url, mode="RAW")

