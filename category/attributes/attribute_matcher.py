# category/attributes/attribute_matcher.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Callable
import re, json

SchemaEntry = Dict[str, Any]
Schema = List[SchemaEntry]
LLMResolver = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class MatchedAttribute:
    category_id: str
    category_attribute_id: int
    attribute_seq: Optional[int]
    attribute_name: str
    classification_type: str
    required: bool
    picked_value_seqs: List[int]
    picked_text: Optional[str]
    debug: Dict[str, Any]


def _norm(s: str) -> str:
    s = s or ""
    s = s.strip().lower()
    s = re.sub(r"\s+", "", s)
    return s


def _safe_int(x) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


def _get_attr(entry: SchemaEntry) -> Optional[Dict[str, Any]]:
    return entry.get("attribute") if isinstance(entry, dict) else None


def _get_id_obj(entry: SchemaEntry) -> Optional[Dict[str, Any]]:
    return entry.get("id") if isinstance(entry, dict) else None


def _build_value_text_index(attr: Dict[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for v in attr.get("attributeValues") or []:
        if not isinstance(v, dict):
            continue
        txt = v.get("attributeValueText") or v.get("minAttributeValue") or ""
        seq = _safe_int(v.get("attributeValueSeq"))
        if txt and seq is not None:
            out[_norm(str(txt))] = seq
    return out


def _allowed_seqs(attr: Dict[str, Any]) -> set[int]:
    out: set[int] = set()
    for v in attr.get("attributeValues") or []:
        s = _safe_int(v.get("attributeValueSeq"))
        if s is not None:
            out.add(s)
    return out


def _max_multi(attr: Dict[str, Any]) -> int:
    n = _safe_int(attr.get("attributeValueMaxMatchingCount"))
    if n is None or n <= 0:
        return 5
    return n


def match_attributes(
    *,
    schema_raw: Schema,
    category_code: str,
    product_name: str,
    option_names: List[str],
    detail_text: str,
    image_urls: Optional[List[str]] = None,
    llm_resolver: Optional[LLMResolver] = None,
    debug: bool = True,
) -> Dict[str, Any]:

    if not llm_resolver:
        raise ValueError("llm_resolver is required")

    llm_input = {
        "category_code": category_code,
        "product_name": product_name,
        "option_names": option_names,
        "detail_text": detail_text,
        "image_urls": image_urls or [],
        "attributes": [],
        "note": (
            "각 attribute는 attributeValues 안에서만 선택하세요. "
            "SINGLE_SELECT는 1개, MULTI_SELECT는 maxMatchingCount 이하로 선택하세요. "
            "TEXT 타입은 문자열만 반환하세요."
        ),
    }

    for entry in schema_raw:
        attr = _get_attr(entry)
        id_obj = _get_id_obj(entry)
        if not attr or not id_obj:
            continue

        caid = _safe_int(id_obj.get("categoryAttributeId"))
        if caid is None:
            continue

        llm_input["attributes"].append({
            "categoryAttributeId": caid,
            "attributeName": attr.get("attributeName"),
            "classificationType": attr.get("attributeClassificationType"),
            "attributeValues": attr.get("attributeValues") or [],
            "maxMatchingCount": _max_multi(attr)
                if attr.get("attributeClassificationType") == "MULTI_SELECT"
                else None,
            "required": bool(entry.get("attributeRequired")),
        })

    if debug:
        print("\n[ATTR][LLM ONLY] resolving attributes")

    llm_result = llm_resolver(llm_input) or {}

    print("\n[DEBUG][LLM RAW RESULT]")
    print(json.dumps(llm_result, ensure_ascii=False, indent=2))

    selections = llm_result.get("selections", {}) or {}

    print("\n[DEBUG][LLM SELECTIONS ONLY]")
    print(json.dumps(selections, ensure_ascii=False, indent=2))

    print("\n[DEBUG][LLM SELECTIONS KEY TYPES]")
    for k in selections.keys():
        print(f"  key={k!r}, type={type(k)}")

    matched_map: Dict[int, MatchedAttribute] = {}

    for entry in schema_raw:
        attr = _get_attr(entry)
        id_obj = _get_id_obj(entry)
        if not attr or not id_obj:
            continue

        caid = _safe_int(id_obj.get("categoryAttributeId"))
        if caid is None:
            continue

        v = selections.get(str(caid)) or selections.get(caid)
        if v is None:
            continue

        attribute_seq = _safe_int(attr.get("id"))
        attribute_name = str(attr.get("attributeName") or "").strip()
        classification = str(attr.get("attributeClassificationType") or "").strip()
        required = bool(entry.get("attributeRequired"))
        category_id = str((id_obj.get("categoryId") or category_code) or "")

        picked_value_seqs: List[int] = []
        picked_text: Optional[str] = None

        if classification in ("SINGLE_SELECT", "MULTI_SELECT"):
            allowed = _allowed_seqs(attr)
            value_text_index = _build_value_text_index(attr)

            raw_list = v if isinstance(v, list) else [v]
            for x in raw_list:
                xi = _safe_int(x)
                if xi is not None and xi in allowed:
                    picked_value_seqs.append(xi)
                    continue
                if isinstance(x, str):
                    seq = value_text_index.get(_norm(x))
                    if seq is not None and seq in allowed:
                        picked_value_seqs.append(seq)

            if classification == "SINGLE_SELECT":
                picked_value_seqs = picked_value_seqs[:1]
            else:
                picked_value_seqs = picked_value_seqs[: _max_multi(attr)]

            if not picked_value_seqs:
                continue

        else:
            if isinstance(v, str) and v.strip():
                picked_text = v.strip()
            else:
                continue

        matched_map[caid] = MatchedAttribute(
            category_id=category_id,
            category_attribute_id=caid,
            attribute_seq=attribute_seq,
            attribute_name=attribute_name,
            classification_type=classification,
            required=required,
            picked_value_seqs=picked_value_seqs,
            picked_text=picked_text,
            debug={"picked_by": "llm"},
        )

    matched = list(matched_map.values())
    payload: List[Dict[str, Any]] = []

    for m in matched:
        if m.classification_type in ("SINGLE_SELECT", "MULTI_SELECT"):
            payload.append({
                "categoryAttributeId": m.category_attribute_id,
                "attributeValueSeqs": m.picked_value_seqs,
            })
        else:
            payload.append({
                "categoryAttributeId": m.category_attribute_id,
                "attributeValueText": m.picked_text,
            })

    if debug:
        print("[ATTR][LLM ONLY] matched =", len(matched))
        print("[ATTR][LLM ONLY] payload =", len(payload))

    return {
        "matched": [
            {
                "categoryId": m.category_id,
                "categoryAttributeId": m.category_attribute_id,
                "attributeSeq": m.attribute_seq,
                "attributeName": m.attribute_name,
                "classificationType": m.classification_type,
                "required": m.required,
                "pickedValueSeqs": m.picked_value_seqs,
                "pickedText": m.picked_text,
                "debug": m.debug,
            }
            for m in matched
        ],
        "payload": payload,
        "unmatched_required": [],
        "debug": {
            "trace": {
                "mode": "llm_only",
                "llm_raw": llm_result,
            }
        },
    }
