from llm.llm_client import request_llm, request_llm_with_image, get_prompt


def generate_product_name_from_llm(product_name: str, keywords: list[str]) -> str:
    """
    Text-only product name generation.
    """
    keyword_str = ", ".join(keywords) if keywords else ""

    prompt = get_prompt("NAME").format(
        ORIGINAL_NAME=product_name,
        P_KEYWORDS=keyword_str,
    )

    return request_llm(prompt)


def generate_product_name_from_llm_with_image(product_name: str, keywords: list[str], image_url: str) -> str:
    """
    Vision-based product name generation.
    """
    keyword_str = ", ".join(keywords) if keywords else ""

    prompt = get_prompt("NAME_VISION").format(
        ORIGINAL_NAME=product_name,
        P_KEYWORDS=keyword_str,
    )

    print("\n================= [LLM PROMPT - VISION MODE] =================")
    print(prompt)
    print("===============================================================\n")

    return request_llm_with_image(prompt, image_url)


def generate_compact_search_query_from_llm(product_name: str, brand: str, max_len: int = 55) -> str:
    """
    Search-focused compact query generator.
    This is intentionally separate from product-name generation.
    """
    prompt = get_prompt("SEARCH_COMPACT").format(
        MAX_LEN=max_len,
        BRAND=brand,
        ORIGINAL_NAME=product_name,
    )

    out = request_llm(prompt)
    if not out:
        return ""

    return out.strip().splitlines()[0].strip()


def generate_canonical_brand_from_llm(
    raw_brand: str,
    product_name: str = "",
) -> str:
    prompt = get_prompt("BRAND_CANONICAL").format(
        RAW_BRAND=raw_brand,
        PRODUCT_NAME=product_name or "",
    )
    out = request_llm(prompt)
    if not out:
        return ""
    return out.strip().splitlines()[0].strip()
