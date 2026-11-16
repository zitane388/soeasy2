# scrapers/uniqlo/vn_scraper.py
from scrapers.base_scraper import BaseScraper
from parsers.product_pages.uniqlo.url_utils import replace_color_code
from parsers.product_pages.uniqlo.parser_vn import build_size_url


class UniqloVNScraper(BaseScraper):

    SITE_KEY = "uniqlo_vn"

    def request_main(self, url):
        print(f"[VN_SCRAPER][MAIN] request_main url = {url}")
        html = self._request_html(url, mode="RAW")
        print(f"[VN_SCRAPER][MAIN] response len = {len(html) if html else 'None'}")
        return html

    def request_color_html(self, url, color_code):
        new_url = replace_color_code(url, color_code)
        print(f"[VN_SCRAPER][COLOR] color_code = {color_code}")
        print(f"[VN_SCRAPER][COLOR] url = {new_url}")

        html = self._request_html(
            new_url,
            mode="COLOR",
            color=color_code
        )

        print(
            f"[VN_SCRAPER][COLOR] response len = "
            f"{len(html) if html else 'None'}"
        )
        return html

    def request_size_html(self, product_code, size_code):
        url = build_size_url(product_code, size_code)

        print(f"[VN_SCRAPER][SIZE] url = {url}")

        html = self._request_html(
            url,
            mode="SIZE",
            size=size_code
        )

        print(
            f"[VN_SCRAPER][SIZE] response len = "
            f"{len(html) if html else 'None'}"
        )
        return html






