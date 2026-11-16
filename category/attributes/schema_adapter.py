# category/attributes/schema_adapter.py

from typing import Dict, List, Any


def adapt_schema_for_matching(
    raw_schema: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    LLM / 규칙 매칭 전용
    """
    schema: List[Dict[str, Any]] = []

    for entry in raw_schema:
        attr = entry.get("attribute")
        if not attr:
            continue

        normalized = {
            "attribute_id": attr.get("id"),
            "attribute_name": attr.get("attributeName"),
            "required": bool(entry.get("attributeRequired")),
            "type": attr.get("attributeClassificationType"),
            "values": [],
        }

        for v in attr.get("attributeValues", []):
            if v.get("attributeValueSeq") and v.get("attributeValueText"):
                normalized["values"].append(
                    {
                        "value_seq": v["attributeValueSeq"],
                        "text": v["attributeValueText"],
                    }
                )

        schema.append(normalized)

    return schema
