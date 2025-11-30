from scrapers.base_scraper import BaseScraper
from utils.url_utils import replace_color_code_jp


class UniqloJPScraper(BaseScraper):

    def request_main_html(self, url):
        return self._request_raw(url, intent="RAW_MAIN")

    def request_color_html(self, url, color_code):
        new_url = replace_color_code_jp(url, color_code)
        return self._request_raw(new_url, intent="RAW_COLOR", color=color_code)
