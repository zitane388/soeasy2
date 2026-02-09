# brand_manager.py

from parsers.product_pages.uniqlo.uniqlo_manager import UniqloParserManager
from parsers.product_pages.gu.gu_manager import GUParserManager
from parsers.product_pages.muji.muji_manager import MujiParserManager

class BrandParserManager:
    """
    URL → 브랜드 라우팅 담당
    """

    def __init__(self):
        print("[INIT] BrandParserManager: 브랜드 라우터들을 로드합니다...")
        # 브랜드별 최상위 라우팅 담당 매니저
        self.brand_managers = [
            UniqloParserManager(),   # 유니클로 라우터
            GUParserManager(),       # ★ GU 일본 라우터
            MujiParserManager(),
        ]
        print(f"[INIT] 로드 완료: {len(self.brand_managers)}개의 브랜드 매니저 활성화.")

    def get_parser(self, url: str):
        """
        URL을 분석하여 브랜드 매니저에게 전달하고,
        국가별 파서(parser), 브랜드명(brand), 국가코드(country)를 반환한다.
        """
        print(f"[ROUTE] 입력된 URL 분석 시작: {url}")

        for bm in self.brand_managers:
            # bm.match(url) 호출 시 어떤 브랜드 매니저가 검사 중인지 로그 출력
            # (bm.__class__.__name__은 UniqloParserManager 등을 출력함)
            manager_name = bm.__class__.__name__
            
            if bm.match(url):
                print(f"[ROUTE] 매칭 성공: {manager_name}가 이 URL을 처리합니다.")
                
                result = bm.get_country_parser(url)
                
                if result:
                    print(f"[ROUTE] 최종 파서 할당 완료: 브랜드={result.get('brand')}, 국가={result.get('country')}")
                else:
                    print(f"[ERROR] {manager_name} 내부에서 파서를 찾는 데 실패했습니다.")
                
                return result
            
            # 매칭되지 않은 경우 (DEBUG용으로 작게 남길 수 있음)
            # print(f"[DEBUG] {manager_name}: 매칭되지 않음")

        # 모든 루프를 돌았는데 매칭되는 브랜드 없음
        print(f"[ERROR] 지원하지 않는 도메인 또는 잘못된 URL입니다: {url}")
        return None