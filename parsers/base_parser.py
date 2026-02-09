import json
from bs4 import BeautifulSoup

class BaseParser:
    """
    모든 사이트 파서가 공통으로 상속해야 하는 기본 클래스.
    사이트별 파서는 extract_xxx() 메서드만 재정의하면 됨.
    """

    def __init__(self, rules_path=None):
        self.rules = {}
        if rules_path:
            self.load_rules(rules_path)

    # ------------------------------------------------------
    # 규칙(JSON) 로드
    # ------------------------------------------------------
    def load_rules(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.rules = json.load(f)
        except Exception:
            self.rules = {}

    # ------------------------------------------------------
    # HTML 파싱 시작
    # ------------------------------------------------------
    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")

        return {
            "name": self.extract_name(soup),
            "price": self.extract_price(soup),
            "images": self.extract_images(soup),
            "options": self.extract_options(soup)
        }

    # ------------------------------------------------------
    # 아래 extract 계열은 개별 사이트 파서가 오버라이딩해서 구현
    # ------------------------------------------------------
    def extract_name(self, soup):
        """
        rules["product_name"]에 있는 셀렉터들을 기반으로 상품명 추출
        """
        selectors = self.rules.get("product_name", [])
        for sel in selectors:
            tag = soup.select_one(sel)
            if tag:
                return self.clean_text(tag.get_text())
        return None

    def extract_price(self, soup):
        """
        rules["price"] 셀렉터 기반으로 가격 추출
        """
        selectors = self.rules.get("price", [])
        for sel in selectors:
            tag = soup.select_one(sel)
            if tag:
                return self.clean_text(tag.get_text())
        return None

    def extract_images(self, soup):
        """
        rules["image"] 셀렉터 기반으로 이미지 URL 수집
        """
        selectors = self.rules.get("image", [])
        images = []

        for sel in selectors:
            for tag in soup.select(sel):
                src = tag.get("src") or tag.get("data-src")
                if src and src not in images:
                    images.append(src)

        return images

    def extract_options(self, soup):
        """
        색상/사이즈 등 옵션 추출 기본 구조
        """
        result = {}

        # 색상
        color_selectors = self.rules.get("color", [])
        colors = self._extract_option_by_selectors(soup, color_selectors)
        if colors:
            result["color"] = colors

        # 사이즈
        size_selectors = self.rules.get("size", [])
        sizes = self._extract_option_by_selectors(soup, size_selectors)
        if sizes:
            result["size"] = sizes

        return result

    # ------------------------------------------------------
    # 공통 옵션 추출 유틸
    # ------------------------------------------------------
    def _extract_option_by_selectors(self, soup, selectors):
        options = []
        for sel in selectors:
            for tag in soup.select(sel):
                label = (
                    tag.get("aria-label")
                    or tag.get("title")
                    or tag.get_text(strip=True)
                )
                if label:
                    cleaned = self.clean_text(label)
                    if cleaned and cleaned not in options:
                        options.append(cleaned)
        return options

    # ------------------------------------------------------
    # 공통 문자열 정리
    # ------------------------------------------------------
    def clean_text(self, text):
        if not text:
            return None

        text = text.strip()

        # 공통 trim chars
        trim_chars = self.rules.get("trim_chars", [])
        for t in trim_chars:
            text = text.replace(t, "")

        return text.strip()
