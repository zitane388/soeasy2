import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import re
import urllib.parse


def clean_and_split(text):
    words = re.findall(r'[\uac00-\ud7a3a-zA-Z0-9]+', text)

    filtered = []
    for w in words:
        # 🔥 영문 단독, 숫자 단독 제거
        if re.fullmatch(r'[a-zA-Z]+', w):
            continue
        if re.fullmatch(r'[0-9]+', w):
            continue
        filtered.append(w)

    return filtered


# ==========================================================
# 🔥 상품명 기반 네이버 연관검색 키워드 자동 추출 함수
# ==========================================================
def extract_keywords(product_name: str) -> list:
    """
    product_name → 네이버 검색 → 연관 키워드 추출 → 리스트 반환
    """
    query = urllib.parse.quote(product_name)
    url = f"https://search.naver.com/search.naver?where=nexearch&query={query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    keywords = set()

    # ==========================================================
    # A 조건: mark 포함 span (제품명과 연관 높은 키워드)
    # ==========================================================
    for ul in soup.find_all("ul", class_="_1RbzoNnJ"):
        for span in ul.find_all("span"):
            if span.find("mark"):
                for child in span.children:
                    text = child.get_text(strip=True) if isinstance(child, Tag) else str(child)
                    for word in clean_and_split(text):
                        keywords.add(word)

    # ==========================================================
    # B 조건: KoFfoLbL 내부 class 없는 span
    # ==========================================================
    for ul in soup.find_all("ul", class_="KoFfoLbL"):
        for span in ul.find_all("span"):
            if not span.get("class"):  # class 없는 경우만
                for word in clean_and_split(span.get_text(strip=True)):
                    keywords.add(word)

    # 반환 (정렬된 리스트)
    return sorted(keywords)
