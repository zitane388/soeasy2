# parser_manager.py
from parsers.product_pages.brand_manager import BrandParserManager


class ParserManager:
    """
    브랜드 → 국가 → 개별 파서까지 자동 선택.
    BrandParserManager가 브랜드 라우팅 전체를 담당한다.
    """

    def __init__(self):
        self.brand_manager = BrandParserManager()

    def get_parser(self, url: str):
        """
        반환값 구조:
        {
            "parser": parser_instance,
            "brand": "uniqlo",
            "country": "jp"
        }
        또는 None
        """

        print(f"[ParserManager] URL 수신 → {url}")

        info = self.brand_manager.get_parser(url)

        if info is None:
            print("[ParserManager] 브랜드 매칭 실패 → None 반환")
            return None

        print(f"[ParserManager] 선택된 파서 → {info['brand']} / {info['country']}")
        return info
