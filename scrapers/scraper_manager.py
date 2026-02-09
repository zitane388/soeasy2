# scrapers/scraper_manager.py

from scrapers.scraper_factory import ScraperFactory
from parsers.product_pages.parser_manager import ParserManager
from utils.currency_utils import normalize_price_to_krw
import re
import time

class ScraperManager:

    def __init__(self):
        print("[INIT] ScraperManager 초기화 중...")
        self.parser_manager = ParserManager()
        self.scraper_factory = ScraperFactory()
        print("[INIT] 파서 및 스크래퍼 로드 완료.")

    def contains_korean(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.search(r"[가-힣]", text))

    def collect(self, url: str):
        start_time = time.time()
        print(f"\n{'='*50}")
        print(f"[JOB START] URL: {url}")
        print(f"{'='*50}")

        # 1) Scraper 선택
        print("[STEP 1] 사이트에 적합한 스크래퍼 탐색 중...")
        scraper = self.scraper_factory.get_scraper(url)
        if scraper is None:
            print("[ERROR] 지원하지 않는 사이트입니다.")
            return {"error": "지원하지 않는 사이트"}
        print(f"[DEBUG] 스크래퍼 선택 완료: {scraper.__class__.__name__}")

        # 2) Parser 선택
        print("[STEP 2] 상품 정보를 읽어올 파서 매칭 중...")
        parser_info = self.parser_manager.get_parser(url)
        if not parser_info:
            print("[ERROR] 해당 URL을 처리할 파서가 없습니다.")
            return {"error": "파서 없음"}

        parser = parser_info["parser"]
        brand = parser_info["brand"]
        country = parser_info["country"]
        print(f"[DEBUG] 매칭 완료: 브랜드={brand}, 국가={country}, 파서={parser.__class__.__name__}")

        # 3) 메인 HTML 수집
        print("[STEP 3] 메인 페이지 데이터(HTML) 수집 시작...")
        try:
            main_html = scraper.request_main(url)
            if not main_html:
                print("[ERROR] 메인 HTML 수집 실패 (내용이 비어있음)")
                return {"error": "메인 HTML 수집 실패"}
            print(f"[DEBUG] HTML 수집 완료 (길이: {len(main_html)} 자)")
        except Exception as e:
            print(f"[ERROR] HTML 요청 중 예외 발생: {str(e)}")
            return {"error": f"요청 에러: {str(e)}"}

        # 4) 파싱 실행
        print("[STEP 4] 데이터 파싱 및 가공 시작 (이미지/가격/옵션)...")
        try:
            results = parser.parse(
                scraper=scraper,
                original_url=url,
                first_html=main_html
            )
            
            if not results:
                print("[ERROR] 파싱 결과가 없습니다.")
                return {"error": "파싱 실패"}
                
            print(f"[DEBUG] 파싱 완료: {len(results)}개의 상품 데이터 추출됨")

            # 가격 환율 적용
            print("[STEP 5] 가격 데이터 통화 최적화(KRW) 중...")
            results = normalize_price_to_krw(
                results,
                country=country
            )
        except Exception as e:
            print(f"[ERROR] 파싱 과정 중 치명적 오류 발생: {str(e)}")
            return {"error": f"파싱 에러: {str(e)}"}

        elapsed_time = time.time() - start_time
        print(f"{'='*50}")
        print(f"[JOB SUCCESS] 전체 소요 시간: {elapsed_time:.2f}초")
        print(f"{'='*50}\n")

        return {
            "parsed": results,
            "brand": brand,
            "country": country,
        }