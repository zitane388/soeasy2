import time
import urllib.parse
import html_receiver
from browser_launcher import open_in_chrome


class BaseScraper:

    # -----------------------------
    # RAW HTML 요청 (공통)
    # -----------------------------
    def _request_raw(self, url, intent="RAW_MAIN", color=None, timeout=60):
        html_receiver.CAPTURED_HTML = None

        suffix = f"#program=SOEASY2&intent={intent}"
        if color:
            suffix += f"&color={color}"

        capture_url = url + suffix

        open_in_chrome(capture_url)
        time.sleep(5)

        start = time.time()
        while time.time() - start < timeout:
            if html_receiver.CAPTURED_HTML:
                return html_receiver.CAPTURED_HTML
            time.sleep(0.2)

        print("[BaseScraper] TIMEOUT:", url)
        return None

    # -----------------------------
    # 자식 Scraper가 반드시 override
    # -----------------------------
    def request_main_html(self, url):
        raise NotImplementedError

    def request_color_html(self, url, color_code):
        return None

    def request_size_chart_html(self, url, size_code=None):
        return None