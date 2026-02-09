from category.attributes.schema_loader import load_raw_attribute_schema
from category.attributes.attribute_matcher import match_attributes
import requests

def auto_match_attributes(
    *,
    category_code: str,
    product_name: str,
    option_names: list[str],
    detail_text: str,
    image_urls: list[str] | None,
    llm_resolver,                 # ← default 제거
    session: requests.Session,
):

    """
    Attribute 자동 매칭 파이프라인
    - 로그인된 SmartStore session 필수
    """

    if session is None:
        raise ValueError("logged-in session is required for attribute matching")

    # 1️⃣ attribute schema 로드 (로그인 세션 사용)
    schema = load_raw_attribute_schema(
        category_code=category_code,
        session=session,
    )

    # 2️⃣ attribute 매칭
    result = match_attributes(
        schema_raw=schema,
        category_code=category_code,
        product_name=product_name,
        option_names=option_names,
        detail_text=detail_text,
        image_urls=image_urls,
        llm_resolver=llm_resolver,
        debug=True,
    )
    
    if not result.get("matched"):
        print("[ATTR] LLM 매칭 실패 → UI 반영 스킵")
        return {
            "matched": [],
            "payload": [],
            "unmatched_required": [],
            "error": "llm_failed",
        }

    return result
