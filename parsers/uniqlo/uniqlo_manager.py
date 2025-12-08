# parsers/uniqlo/uniqlo_manager.py

import os
import json
from urllib.parse import urlparse

from .parser_jp import UniqloJapanParser
from .parser_vn import UniqloVietnamParser   # ★ 추가

BRAND = "유니클로"


class UniqloParserManager:

    # ---------------------------------------------
    # Uniqlo URL 여부 판단
    # ---------------------------------------------
    def match(self, url: str):
        return "uniqlo.com" in url.lower()

    # ---------------------------------------------
    # 국가별 파서 선택
    # ---------------------------------------------
    def get_country_parser(self, url: str):
        parsed = urlparse(url)
        path = parsed.path.lower()

        # ------------------------------
        # 일본 사이트
        # ------------------------------
        if "/jp/" in path:
            return self._get("jp", UniqloJapanParser)

        # ------------------------------
        # 베트남 사이트
        # ------------------------------
        if "/vn/" in path:
            return self._get("vn", UniqloVietnamParser)

        # ------------------------------
        # 미매칭
        # ------------------------------
        print("[UniqloParserManager] 국가 매칭 실패 → None")
        return None

    # ---------------------------------------------
    # 국가 공통 처리: rules + parser 묶어서 반환
    # ---------------------------------------------
    def _get(self, country_code, parser_cls):
        rules = self._load_rules(f"{country_code}.json")
        parser = parser_cls(rules, BRAND)

        return {
            "parser": parser,
            "brand": BRAND,
            "country": country_code
        }

    # ---------------------------------------------
    # 규칙 파일 로드
    # ---------------------------------------------
    def _load_rules(self, filename):
        path = os.path.join("rules", "uniqlo", filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
