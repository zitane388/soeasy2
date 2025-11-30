# brand_manager.py

from parsers.uniqlo.uniqlo_manager import UniqloParserManager
from parsers.gu.gu_manager import GUParserManager


class BrandParserManager:
    """
    URL → 브랜드 라우팅 담당
    """

    def __init__(self):
        # 브랜드별 최상위 라우팅 담당 매니저
        self.brand_managers = [
            UniqloParserManager(),   # 유니클로 라우터
            GUParserManager(),       # ★ GU 일본 라우터
        ]

    def get_parser(self, url: str):
        """
        URL을 분석하여 브랜드 매니저에게 전달하고,
        국가별 파서(parser), 브랜드명(brand), 국가코드(country)를 반환한다.

        반환 구조:
        {
            "parser": parser_instance,
            "brand": "uniqlo" 또는 "gu",
            "country": "jp"
        }
        """

        for bm in self.brand_managers:
            if bm.match(url):
                return bm.get_country_parser(url)

        # 매칭되는 브랜드 없음
        return None
