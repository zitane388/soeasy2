# scrapers/uniqlo/jp_scraper.py
from scrapers.base_scraper import BaseScraper
from parsers.product_pages.uniqlo.url_utils import replace_color_code

class UniqloJPScraper(BaseScraper):
    
    SITE_KEY = "uniqlo_jp"

    def request_main(self, url):
        return self._request_html(url, mode="RAW")          # RAW = 메인HTML

    def request_color_html(self, url, color_code):
        new_url = replace_color_code(url, color_code)
        return self._request_html(new_url, mode="COLOR", color=color_code) 
