# llm_product_name_generator.py

from llm.llm_client import request_llm, request_llm_with_image, get_prompt

def generate_product_name_from_llm(product_name: str, keywords: list[str]) -> str:
    """
    텍스트-only 상품명 생성
    """
    keyword_str = ", ".join(keywords) if keywords else ""

    prompt = get_prompt("NAME").format(
        ORIGINAL_NAME = product_name,
        P_KEYWORDS    = keyword_str,
    )

    return request_llm(prompt)


def generate_product_name_from_llm_with_image(product_name: str, keywords: list[str], image_url: str) -> str:
    """
    Vision 기반 상품명 생성 (이미지 URL 사용)
    """
    keyword_str = ", ".join(keywords) if keywords else ""

    prompt = get_prompt("NAME_VISION").format(
        ORIGINAL_NAME = product_name,
        P_KEYWORDS    = keyword_str,
    )
    
    print("\n================= [LLM PROMPT - VISION MODE] =================")
    print(prompt)
    print("===============================================================\n")

    # 🔥 여기서도 'image_url' 그대로 넘김
    return request_llm_with_image(prompt, image_url)
