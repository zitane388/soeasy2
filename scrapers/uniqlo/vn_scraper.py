from scrapers.base_scraper import BaseScraper


class UniqloVNScraper(BaseScraper):

    def request_main_html(self, url):
        return self._request_raw(url, intent="RAW_MAIN")

    def request_color_html(self, url, color_code):
        if "?" in url:
            new_url = url.split("?")[0] + f"?colorCode={color_code}"
        else:
            new_url = url + f"?colorCode={color_code}"

        return self._request_raw(new_url, intent="RAW_COLOR", color=color_code)

    def request_size_chart_html(self, url, size_code):
        base = url.split("?")[0]
        size_url = f"{base}/size?sizeCode={size_code}&measurementUnit=cm"
        return self._request_raw(size_url, intent="RAW_SIZE")
