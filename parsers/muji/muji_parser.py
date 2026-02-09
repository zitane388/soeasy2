# parsers/muji_parser.py
from ..base_parser import BaseParser
from bs4 import BeautifulSoup

class MujiParser(BaseParser):
    """
    무인양품(MUJI) 상품 페이지 파서 기본 골격.
    match()로 URL 판별, parse()에서 HTML 파싱.
    """

    def match(self, url: str) -> bool:
        return "muji.com" in url or "muji" in url

    def parse(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")

        name = ""
        price = ""

        # MUJI 기본 상품명 탐색 (일본 사이트 기준)
        name_tag = soup.find("h1")
        if name_tag:
            name = name_tag.get_text(strip=True)

        # MUJI 가격 탐색 (자주 쓰는 클래스)
        price_tag = soup.find("span", class_="price")
        if price_tag:
            price = price_tag.get_text(strip=True)

        return {
            "name": name,
            "price": price,
            "images": [],
            "options": []
        }
