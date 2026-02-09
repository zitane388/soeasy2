# parsers/product_pages/muji/muji_manager.py

import json
import os
from urllib.parse import urlparse

from .parser_jp import MujiJapanParser
from utils.path import p

BRAND = "무인양품"

class MujiParserManager:

    def match(self, url: str):
        is_match = "muji.com" in url.lower()
        if is_match:
            print(f"[MATCH] {BRAND}: URL 매칭 확인됨.")
        return is_match

    def get_country_parser(self, url: str):
        path = urlparse(url).path.lower()
        print(f"[MATCH] {BRAND}: 국가 코드 분석 중... (Path: {path})")

        if "/jp/" in path:
            print(f"[MATCH] {BRAND}: 일본(JP) 지역 파서 선택.")
            return self._get("jp", MujiJapanParser)

        print(f"[WARN] {BRAND}: 지원하지 않는 국가 경로입니다. (URL: {url})")
        return None

    def _get(self, country_code, parser_cls):
        try:
            rules = self._load_rules(f"{country_code}.json")
            parser = parser_cls(rules, BRAND)

            print(f"[DEBUG] {BRAND}: {country_code.upper()} 파서 객체 생성 완료.")
            return {
                "parser": parser,
                "brand": BRAND,
                "country": country_code
            }
        except Exception as e:
            print(f"[ERROR] {BRAND}: {country_code.upper()} 파서 준비 중 오류 발생: {str(e)}")
            return None

    def _load_rules(self, filename):
        json_path = p("parsers", "product_pages", "rules", "muji", filename)
        print(f"[FILES] 설정 파일 로딩 시도: {json_path}")

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Missing config file: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"[FILES] 설정 파일 로드 성공: {filename}")
            return data
