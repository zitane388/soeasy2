import requests
from bs4 import BeautifulSoup, Tag
import re
import urllib.parse


def clean_and_split(text):
    words = re.findall(r'[\uac00-\ud7a3a-zA-Z0-9]+', text)

    filtered = []
    for w in words:
        # 영문 단독, 숫자 단독 제거
        if re.fullmatch(r'[a-zA-Z]+', w):
            continue
        if re.fullmatch(r'[0-9]+', w):
            continue
        filtered.append(w)

    return filtered


# 🔥 한글 포함 여부 체크
def has_korean(text: str) -> bool:
    return bool(re.search(r'[가-힣]', text))


def extract_keywords(product_name: str, brand: str) -> list:
    
    print(
        f"[KEYWORD_EXTRACT][INPUT] "
        f"product_name='{product_name}' | "
        f"brand='{brand}' | "
        f"has_korean={has_korean(product_name) if product_name else False}"
    )
    
    query = urllib.parse.quote(product_name)
    url = f"https://search.naver.com/search.naver?where=nexearch&query={query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    keywords = set()
    brand = brand.strip().lower()

    # ==========================================================
    # A 조건: mark 포함 span + a>span(class 없음)
    # ==========================================================
    A_CLASSES = ["_1RbzoNnJ", "dVWEbQ7N"]

    for cls in A_CLASSES:
        for ul in soup.find_all("ul", class_=cls):

            for li in ul.find_all("li"):

                li_words = []  # ← 이 li에서 추출된 모든 단어

                # ----- mark 포함 span -----
                for span in li.find_all("span"):
                    if span.find("mark"):
                        for child in span.children:
                            text = child.get_text(strip=True) if isinstance(child, Tag) else str(child)
                            for word in clean_and_split(text):
                                li_words.append(word)

                # ----- li > a > span (class 없음) -----
                for a in li.find_all("a"):
                    for span in a.find_all("span"):
                        if not span.get("class"):
                            text = span.get_text(strip=True)
                            for word in clean_and_split(text):
                                li_words.append(word)

                # ----- 한글 포함 단어만 남기기 -----
                li_words = [w for w in li_words if has_korean(w)]

                # ----- 브랜드 포함 여부 체크 -----
                if any(brand in w.lower() for w in li_words):
                    keywords.update(li_words)
                # 브랜드 없는 li는 버림


    # ==========================================================
    # B 조건: KoFfoLbL 내부 class 없는 span만
    # ==========================================================
    for ul in soup.find_all("ul", class_="KoFfoLbL"):

        for li in ul.find_all("li"):
            li_words = []

            for span in li.find_all("span"):
                if not span.get("class"):
                    text = span.get_text(strip=True)
                    for word in clean_and_split(text):
                        li_words.append(word)

            li_words = [w for w in li_words if has_korean(w)]

            # 브랜드 포함 li만 반영
            if any(brand in w.lower() for w in li_words):
                keywords.update(li_words)

    result = sorted(keywords)

    # 🔍 [DEBUG] 키워드 추출 결과 로그
    print(
        f"[KEYWORD_EXTRACT] brand='{brand}' | "
        f"input='{product_name}' | "
        f"count={len(result)} | "
        f"keywords={result}"
    )

    return result

