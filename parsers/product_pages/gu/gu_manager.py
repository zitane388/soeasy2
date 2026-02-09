# parsers/gu/gu_manager.py

import json
from urllib.parse import urlparse

from .parser_jp import GUJapanParser
from utils.path import p   # ✅ 추가

BRAND = "GU"


class GUParserManager:

    def match(self, url: str):
        netloc = urlparse(url).netloc.lower()
        return "gu" in netloc

    def get_country_parser(self, url: str):
        path = urlparse(url).path.lower()

        if "/jp/" in path:
            return self._get_japan()

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
        path = p(
            "parsers",
            "product_pages",
            "rules",
            "gu",
            filename
        )

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

