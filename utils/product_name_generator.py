from llm.llm_product_name_generator import (
    generate_product_name_from_llm,
    generate_product_name_from_llm_with_image,
)

def generate_final_name(translated_name: str, keyword_list: list[str], image_url: str = None) -> str:
    """
    translated_name : 일본어/영어 → 한국어 번역된 상품명
    keyword_list    : 후보 키워드 리스트
    image_url       : 선택된 대표 이미지의 URL (http로 시작하는 주소)
    """

    if not translated_name or not keyword_list:
        print("[SKIP] 상품명 생성 불가 - 번역명 또는 키워드 없음")
        return ""

    # 1) 이미지 있으면 → Vision 버전
    if image_url and image_url.startswith("http"):
        print(f"[LLM] 상품명 생성 시작 (Vision) → {translated_name}")
        result = generate_product_name_from_llm_with_image(
            product_name = translated_name,
            keywords     = keyword_list,
            image_url    = image_url,   # 🔥 여기서는 'URL' 그대로 전달
        )
    else:
        # 2) 이미지 없으면 → 텍스트-only
        print(f"[LLM] 상품명 생성 시작 (Text) → {translated_name}")
        result = generate_product_name_from_llm(
            product_name = translated_name,
            keywords     = keyword_list,
        )

    print(f"[LLM] 상품명 생성 완료:", result)
    return result
