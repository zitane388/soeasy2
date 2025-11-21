# brand_manager.py
from parsers.uniqlo.uniqlo_manager import UniqloParserManager
# from parsers.muji.muji_manager import MujiParserManager
# from parsers.zara.zara_manager import ZaraParserManager
# … 필요 시 추가

class BrandParserManager:
    """
    URL → 브랜드 라우팅 담당
    """

    def __init__(self):
        self.brand_managers = [
            UniqloParserManager(),
            # MujiParserManager(),
            # ZaraParserManager(),
        ]

    def get_parser(self, url: str):
        for bm in self.brand_managers:
            if bm.match(url):
                return bm.get_country_parser(url)

        return None
