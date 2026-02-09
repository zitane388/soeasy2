from scrapers.base_scraper import BaseScraper
import urllib.parse

class LensScraper(BaseScraper):
    SITE_KEY = "LENS"

    def search(self, img_url: str):
        encoded = urllib.parse.quote(img_url, safe='')
        url = f"https://lens.google.com/uploadbyurl?hl=en&gl=US&url={encoded}"
        return self._request_html(url, mode="LENS_INIT")
