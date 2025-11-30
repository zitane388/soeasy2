# parsers/gu/gu_manager.py

import os
import json
from urllib.parse import urlparse

from .parser_jp import GUJapanParser

BRAND = "GU"

class GUParserManager:

    def match(self, url: str):
        return "gu-global.com" in url.lower()

    def get_country_parser(self, url: str):
        parsed = urlparse(url)
        path = parsed.path.lower()

        # ------------------------------
        # 일본 사이트
        # ------------------------------
        if "/jp/" in path:
            return self._get_japan()

        print("[GUParserManager] 국가 매칭 실패 → None")
        return None

    def _get_japan(self):
        rules = self._load_rules("jp.json")
        parser = GUJapanParser(rules)

        return {
            "parser": parser,
            "brand": BRAND,
            "country": "jp"
        }

    def _load_rules(self, filename):
        path = os.path.join("rules", "gu", filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
