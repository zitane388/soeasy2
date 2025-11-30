# utils/product_name_generator.py

from llm.llm_product_name_generator import generate_product_name_from_llm

def collect_primary_keywords(item):
    """
    1차 키워드 = 옵션 name 전체 → 공백 split
    """
    opts = getattr(item, "options", []) or item.parsed_raw.get("colors", [])
    joined = " ".join([o.get("name", "") for o in opts if o.get("name")])
    keywords = joined.split()  # ← 공백 기준 split
    return keywords


def collect_secondary_keywords(item):
    """
    2차 키워드 = 상세설명 텍스트 전체 → 공백 split
    """
    txt = item.final_detail_text or item.parsed_raw.get("detail_text", "") or ""
    keywords = txt.replace("\n", " ").split()  # 공백 기준 split
    return keywords


def generate_final_name_once(item):
    """
    상품명이 없으면 최초 1회 자동 생성
    """
    if item.final_name:
        return

    p_keywords = collect_primary_keywords(item)
    s_keywords = collect_secondary_keywords(item)

    info = {
        "primary_keywords": p_keywords,
        "secondary_keywords": s_keywords,
        "url": item.url,
    }

    print(f"[LLM] 상품명 생성 시작 → {item.url}")
    item.final_name = generate_product_name_from_llm(info)
    print(f"[LLM] 상품명 생성 완료:", item.final_name)
