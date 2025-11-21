from .parser_jp import MujiJapanParser
from .parser_global import MujiGlobalParser


class MujiParserManager:

    def match(self, url: str):
        return "muji.com" in url

    def get_country_parser(self, url: str):
        # 일본 사이트
        if "muji.com/jp" in url:
            return MujiJapanParser()

        # 그 외 지역은 글로벌 처리
        return MujiGlobalParser()
