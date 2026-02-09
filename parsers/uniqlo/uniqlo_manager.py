# parsers/uniqlo/uniqlo_manager.py

import os
import json

from .parser_jp import UniqloJapanParser
from .parser_us import UniqloUsaParser
from .parser_global import UniqloGlobalParser

# ------------------------------------------------------------------
# 브랜드/국가 상수
# ------------------------------------------------------------------
BRAND = "uniqlo"
COUNTRY_JP = "jp"
COUNTRY_US = "us"
COUNTRY_GLOBAL = "global"

# ------------------------------------------------------------------
# 룰 파일 경로
# ------------------------------------------------------------------
RULES_DIR = os.path.join("rules", "uniqlo")


class UniqloParserManager:
    """
    유니클로 URL을 처리하여 국가별 파서를 반환하는 라우터
    ParserManager → BrandParserManager → UniqloParserManager
    구조 속에서 동작한다.
    """

    # --------------------------------------------------------------
    # 해당 URL이 유니클로인지 확인
    # --------------------------------------------------------------
    def match(self, url: str):
        return "uniqlo.com" in url.lower()

    # --------------------------------------------------------------
    # 국가별 파서 선택
    # 항상 dict 형태로 반환
    # --------------------------------------------------------------
    def get_country_parser(self, url: str):
        url_lower = url.lower()
        print(f"[UniqloParserManager] URL 분석 → {url}")

        # ==========================================================
        # 일본 (JP)
        # ==========================================================
        if "uniqlo.com/jp" in url_lower:
            print("[UniqloParserManager] JP 파서 선택")
            return {
                "parser": UniqloJapanParser(self._load_rules("jp.json")),
                "brand": BRAND,
                "country": COUNTRY_JP
            }

        # ==========================================================
        # 미국 (US)
        # ==========================================================
        if "uniqlo.com/us" in url_lower:
            print("[UniqloParserManager] US 파서 선택")
            return {
                "parser": UniqloUsaParser(self._load_rules("us.json")),
                "brand": BRAND,
                "country": COUNTRY_US
            }

        # ==========================================================
        # 그 외 GLOBAL (기본값)
        # ==========================================================
        print("[UniqloParserManager] GLOBAL 파서 선택")
        return {
            "parser": UniqloGlobalParser(self._load_rules("global.json")),
            "brand": BRAND,
            "country": COUNTRY_GLOBAL
        }

    # --------------------------------------------------------------
    # 룰 파일 로드
    # --------------------------------------------------------------
    def _load_rules(self, filename):
        path = os.path.join(RULES_DIR, filename)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
