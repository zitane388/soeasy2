# category/services/attribute_prefetch.py

from category.attributes.schema_loader import load_raw_attribute_schema
from category.attributes.attribute_pipeline import auto_match_attributes
from llm.llm_attribute_resolver import resolve_attributes_with_llm


def prefetch_category_attributes(
    *,
    item,
    session,
    product_name: str,
    option_names: list[str],
    detail_text: str,
    image_urls: list[str],
):
    """
    카테고리 기준 속성 정보 사전 세팅
    - schema
    - matched
    - payload
    - unmatched_required
    """

    if not item.category_code:
        return False

    # 1️⃣ schema
    schema = load_raw_attribute_schema(
        category_code=item.category_code,
        session=session,
    )
    item.attribute_schema = schema

    # 2️⃣ auto match
    result = auto_match_attributes(
        category_code=item.category_code,
        product_name=product_name,
        option_names=option_names,
        detail_text=detail_text,
        image_urls=image_urls,
        session=session,
        llm_resolver=resolve_attributes_with_llm,
    )

    item.attribute_matched = result.get("matched", [])
    item.attribute_payload = result.get("payload", [])
    item.attribute_unmatched_required = result.get("unmatched_required", [])

    return True
