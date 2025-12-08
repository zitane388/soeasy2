# scrapers/scraper_manager.py

import time
import urllib.parse
import html_receiver

from scrapers.scraper_factory import ScraperFactory
from parser_manager import ParserManager
from utils.utils_translator import translate_to_korean   # 아직 사용중일 가능성 있음
from browser_launcher import open_in_chrome
import re

class ScraperManager:

    def __init__(self):
        self.parser_manager = ParserManager()
        self.scraper_factory = ScraperFactory()

    def contains_korean(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.search(r"[가-힣]", text))


    # ------------------------------------------------------
    # 본체 파이프라인 실행
    # ------------------------------------------------------
    def collect(self, url: str):

        # -----------------------------
        # 1) Scraper 선택
        # -----------------------------
        scraper = self.scraper_factory.get_scraper(url)
        if scraper is None:
            return {"error": "지원하지 않는 사이트"}

        # -----------------------------
        # 2) Parser 선택
        # -----------------------------
        parser_info = self.parser_manager.get_parser(url)
        if not parser_info:
            return {"error": "파서 없음"}

        parser = parser_info["parser"]
        brand = parser_info["brand"]
        country = parser_info["country"]

        # -----------------------------
        # 3) 메인 HTML 수집
        # -----------------------------
        main_html = scraper.request_main(url)
        if not main_html:
            return {"error": "메인 HTML 수집 실패"}

        # -----------------------------
        # 4) 파싱 실행
        # -----------------------------
        results = parser.parse(
            scraper=scraper,
            original_url=url,
            first_html=main_html
        )

        return {
            "parsed": results,
            "brand": brand,
            "country": country,
        }

