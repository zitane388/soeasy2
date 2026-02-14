from urllib.parse import urlparse

from .parser_jp import SuperSportsJapanParser


class SuperSportsParserManager:
    BRAND = "supersports"

    def match(self, url: str):
        return "supersports.com" in (url or "").lower()

    def get_country_parser(self, url: str):
        path = urlparse(url).path.lower()
        if "/ja-jp/" in path or "/jp/" in path:
            return {
                "parser": SuperSportsJapanParser(),
                "brand": self.BRAND,
                "country": "jp",
            }
        return None

