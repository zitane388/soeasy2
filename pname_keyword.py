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
    """
    네이버 검색 기반 키워드 추출
    - 절대 블로킹되지 않음
    - 실패 시 빈 리스트 반환
    """

    print(
        f"[KEYWORD_EXTRACT][INPUT] "
        f"product_name='{product_name}' | "
        f"brand='{brand}' | "
        f"has_korean={has_korean(product_name) if product_name else False}"
    )

    if not product_name or not brand:
        print("[KEYWORD_EXTRACT][SKIP] product_name 또는 brand 없음")
        return []

    try:
        query = urllib.parse.quote(product_name)
        url = f"https://search.naver.com/search.naver?where=nexearch&query={query}"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate",
        }

        print("[KEYWORD_EXTRACT] requests.get START")

        resp = requests.get(
            url,
            headers=headers,
            timeout=5  # 🔥 핵심: 무조건 타임아웃
        )

        print(
            "[KEYWORD_EXTRACT] requests.get DONE "
            f"status={resp.status_code} "
            f"len={len(resp.text)}"
        )

        if resp.status_code != 200 or not resp.text:
            print("[KEYWORD_EXTRACT][WARN] 응답 비정상")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        keywords = set()
        brand_l = brand.strip().lower()

        # ==========================================================
        # A 조건: mark 포함 span + a > span(class 없음)
        # ==========================================================
        A_CLASSES = ["_1RbzoNnJ", "dVWEbQ7N"]

        for cls in A_CLASSES:
            for ul in soup.find_all("ul", class_=cls):
                for li in ul.find_all("li"):
                    li_words = []

                    # ----- mark 포함 span -----
                    for span in li.find_all("span"):
                        if span.find("mark"):
                            for child in span.children:
                                text = (
                                    child.get_text(strip=True)
                                    if isinstance(child, Tag)
                                    else str(child)
                                )
                                li_words.extend(clean_and_split(text))

                    # ----- li > a > span (class 없음) -----
                    for a in li.find_all("a"):
                        for span in a.find_all("span"):
                            if not span.get("class"):
                                li_words.extend(
                                    clean_and_split(span.get_text(strip=True))
                                )

                    li_words = [w for w in li_words if has_korean(w)]

                    if any(brand_l in w.lower() for w in li_words):
                        keywords.update(li_words)

        # ==========================================================
        # B 조건: KoFfoLbL 내부 class 없는 span
        # ==========================================================
        for ul in soup.find_all("ul", class_="KoFfoLbL"):
            for li in ul.find_all("li"):
                li_words = []

                for span in li.find_all("span"):
                    if not span.get("class"):
                        li_words.extend(
                            clean_and_split(span.get_text(strip=True))
                        )

                li_words = [w for w in li_words if has_korean(w)]

                if any(brand_l in w.lower() for w in li_words):
                    keywords.update(li_words)

        result = sorted(keywords)

        print(
            f"[KEYWORD_EXTRACT][RESULT] "
            f"brand='{brand_l}' | "
            f"input='{product_name}' | "
            f"count={len(result)} | "
            f"keywords={result}"
        )

        return result

    except Exception as e:
        # 🔥 여기서 절대 프로그램 멈추지 않음
        print("[KEYWORD_EXTRACT][CRASH]", repr(e))
        return []
