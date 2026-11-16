# parsers/uniqlo/uniqlo_manager.py
import json
import os
from urllib.parse import urlparse

from .parser_jp import UniqloJapanParser
from .parser_vn import UniqloVietnamParser
from utils.path import p   # ✅ 경로 처리 유틸리티

BRAND = "유니클로"

class UniqloParserManager:

    def match(self, url: str):
        is_match = "uniqlo.com" in url.lower()
        if is_match:
            print(f"[MATCH] {BRAND}: URL 매칭 확인됨.")
        return is_match

    def get_country_parser(self, url: str):
        path = urlparse(url).path.lower()
        print(f"[MATCH] {BRAND}: 국가 코드 분석 중... (Path: {path})")

        if "/jp/" in path:
            print(f"[MATCH] {BRAND}: 일본(JP) 지역 파서 선택.")
            return self._get("jp", UniqloJapanParser)

        if "/vn/" in path:
            print(f"[MATCH] {BRAND}: 베트남(VN) 지역 파서 선택.")
            return self._get("vn", UniqloVietnamParser)

        print(f"[WARN] {BRAND}: 지원하지 않는 국가 경로입니다. (URL: {url})")
        return None

    def _get(self, country_code, parser_cls):
        try:
            # 설정 파일 로드 시도
            rules = self._load_rules(f"{country_code}.json")
            
            # 파서 인스턴스 생성
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
        # 실행파일 기준 경로로 통일 (p 유틸리티 사용)
        json_path = p("parsers", "product_pages", "rules", "uniqlo", filename)
        
        print(f"[FILES] 설정 파일 로딩 시도: {json_path}")
        
        if not os.path.exists(json_path):
            print(f"[ERROR] 설정 파일을 찾을 수 없습니다: {json_path}")
            raise FileNotFoundError(f"Missing config file: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"[FILES] 설정 파일 로드 성공: {filename} (룰 개수: {len(data)}개)")
            return data