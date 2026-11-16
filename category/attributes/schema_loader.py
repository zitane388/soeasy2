import requests
from typing import Any, List, Dict

SMARTSTORE_ATTRIBUTE_API = (
    "https://sell.smartstore.naver.com/api/category-attribute/attribute-group"
)


class AttributeSchemaLoadError(Exception):
    pass


def _normalize_schema(schema: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    SmartStore 속성 스키마 정규화
    - attributeValues 누락/None 방지
    - attributeValueText / minAttributeValue fallback 정리
    - UI/Matcher에서 그대로 사용 가능하도록 보정
    """
    out: List[Dict[str, Any]] = []

    for entry in schema:
        if not isinstance(entry, dict):
            continue

        attr = entry.get("attribute")
        if not isinstance(attr, dict):
            out.append(entry)
            continue

        values = attr.get("attributeValues")

        if not isinstance(values, list):
            values = []
        else:
            fixed_vals = []
            for v in values:
                if not isinstance(v, dict):
                    continue

                # SmartStore 응답 변형 케이스 방어
                if not v.get("attributeValueText"):
                    if v.get("minAttributeValue") is not None:
                        v["attributeValueText"] = str(v["minAttributeValue"])
                    else:
                        v["attributeValueText"] = ""

                fixed_vals.append(v)

            values = fixed_vals

        attr["attributeValues"] = values
        entry["attribute"] = attr
        out.append(entry)

    return out


def load_raw_attribute_schema(
    *,
    category_code: str,
    session: requests.Session,
) -> List[Dict[str, Any]]:
    if not category_code:
        raise AttributeSchemaLoadError("category_code is required")

    resp = session.get(
        SMARTSTORE_ATTRIBUTE_API,
        params={"leafCategoryId": category_code},
        timeout=10,
    )

    if resp.status_code != 200:
        raise AttributeSchemaLoadError(
            f"HTTP {resp.status_code} from SmartStore API"
        )

    data = resp.json()

    if not isinstance(data, list):
        raise AttributeSchemaLoadError("invalid response format")

    return _normalize_schema(data)
