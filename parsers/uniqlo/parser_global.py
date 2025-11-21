from parsers.base_parser import BaseParser
from bs4 import BeautifulSoup

class UniqloGlobalParser(BaseParser):

    def parse(self, html: str):
        soup = BeautifulSoup(html, "html.parser")

        name = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        price = ""  # 그 외 가격 구조 분석 필요 (나중에 구현)

        return {
            "name": name,
            "price": price,
            "options": [],
            "images": []
        }
        