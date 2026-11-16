# category/matcher/extract_template_keywords.py
# ============================================================
# Extract template keywords from windly_categories.json
# (rule-based, same logic as category_matcher)
# ============================================================

import json
import re
from typing import List, Dict
from utils.path import p


def resolve_template_keywords(template_key: str, categories: Dict[str, str]) -> List[str]:
    """
    category_matcher와 동일한 template_key 분해 로직
    """

    # 1) 카테고리 경로에서 원자 토큰 수집
    atom_tokens = set()

    for path in categories.values():
        steps = re.split(r"[»>]", path)
        for step in steps:
            parts = re.split(r"[ /&·\-()]+", step)
            for part in parts:
                token = part.strip()
                if len(token) >= 2 and token.lower() != "basic":
                    atom_tokens.add(token)

    result = []

    # 2) template_key 단어 단위 처리
    for word in template_key.split():
        remaining = word
        used = []

        # 단어 자체는 분해 후보에서 제외
        candidates = [t for t in atom_tokens if t != word and t in remaining]
        candidates.sort(key=len, reverse=True)

        for token in candidates:
            if token in remaining:
                used.append(token)
                remaining = remaining.replace(token, "", 1)

        # 완전히 분해되면 분해 확정
        if used and remaining == "":
            result.extend(used)
        else:
            result.append(word)

    # 3) 중복 제거 (순서 유지)
    final = []
    seen = set()
    for k in result:
        if k not in seen:
            seen.add(k)
            final.append(k)

    return final


def extract_keywords_from_windly_categories() -> List[str]:
    """
    windly_categories.json을 읽어서
    모든 template_key를 분해 → 전역 키워드 배열 생성
    """

    json_path = p("category", "sources", "windly", "windly_categories.json")

    with open(json_path, encoding="utf-8") as f:
        category_data = json.load(f)

    all_keywords: List[str] = []
    seen = set()

    for item in category_data:
        template_key = item.get("template_key")
        categories = item.get("categories")

        if not template_key or not categories:
            continue

        keywords = resolve_template_keywords(template_key, categories)

        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                all_keywords.append(kw)

    return all_keywords


# ============================================================
# CLI / Debug
# ============================================================

if __name__ == "__main__":
    keywords = extract_keywords_from_windly_categories()

    print("=== WINDLY TEMPLATE KEYWORDS ===")
    for k in keywords:
        print(k)


