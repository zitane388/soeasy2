# scrapers/base_scraper.py
import time, html_receiver
from browser_launcher import open_in_chrome

class BaseScraper:

    def _request_html(self, url, mode="RAW", timeout=60, **kwargs):
        html_receiver.CAPTURED_HTML = None

        # intent 제거 → mode만 유지
        suffix = f"#program=SOEASY2&site={self.SITE_KEY}&mode={mode}"

        for k, v in kwargs.items():
            suffix += f"&{k}={v}"

        full = url + suffix
        print("[OPEN]", full)
        open_in_chrome(full)
        time.sleep(5)

        start = time.time()
        while time.time() - start < timeout:
            if html_receiver.CAPTURED_HTML:
                print("[OK] HTML 수집됨", len(html_receiver.CAPTURED_HTML))
                return html_receiver.CAPTURED_HTML
            time.sleep(0.2)

        print("[TIMEOUT]", full)
        return None

