from parsers.product_pages.gu.gu_manager import GUParserManager
from parsers.product_pages.muji.muji_manager import MujiParserManager
from parsers.product_pages.supersports.supersports_manager import SuperSportsParserManager
from parsers.product_pages.uniqlo.uniqlo_manager import UniqloParserManager


class BrandParserManager:
    def __init__(self):
        self.brand_managers = [
            UniqloParserManager(),
            GUParserManager(),
            MujiParserManager(),
            SuperSportsParserManager(),
        ]

    def get_parser(self, url: str):
        for manager in self.brand_managers:
            if manager.match(url):
                return manager.get_country_parser(url)
        return None

