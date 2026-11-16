
# llm_attribute_resolver.py
from __future__ import annotations
from llm.llm_client import get_prompt, request_llm
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

log = logging.getLogger(__name__)

# 너무 많으면 콘솔이 죽어서 기본 제한을 둡니다.
# "진짜 전부" 찍고 싶으면 여기 숫자를 크게 올리세요. (예: 5000)
MAX_CANDIDATES_TO_LOG = 200
PREVIEW_LIMIT = 1200


def resolve_attributes_with_llm(payload: dict) -> dict:
    log.info("========== [LLM ATTRIBUTE RESOLVE START] ==========")

    # -------------------------------------------------
    # 1) 프롬프트
    # -------------------------------------------------
    prompt = get_prompt("ATTRIBUTE_PICK")
    log.info("[PROMPT] loaded (length=%d)", len(prompt))

    # -------------------------------------------------
    # 2) 입력 요약
    # -------------------------------------------------
    attrs = payload.get("attributes", []) or []
    log.info(
        "[INPUT] category=%s | attr_count=%d | product_name_len=%s | detail_len=%s | image_urls=%d",
        payload.get("category_code"),
        len(attrs),
        len(payload.get("product_name") or "") if isinstance(payload.get("product_name"), str) else None,
        len(payload.get("detail_text") or "") if isinstance(payload.get("detail_text"), str) else None,
        len(payload.get("image_urls") or []),
    )

    # attribute별 간단 요약(후보 전체는 아래에서 상세 출력)
    for a in attrs:
        log.info(
            "[INPUT ATTR] %s (%s) rulePicked=%s",
            a.get("attributeName"),
            a.get("classificationType"),
            _fmt_rule_pick(a),
        )

    # 원하면 payload 전체 pretty는 DEBUG에서만
    log.debug("[INPUT PAYLOAD]\n%s", _pretty(payload, limit=8000))

    # -------------------------------------------------
    # 3) LLM 요청
    # -------------------------------------------------
    try:
        llm_payload = build_llm_attribute_payload(payload)
        payload_json = json.dumps(llm_payload, ensure_ascii=False)
    except Exception as e:
        log.error("[PAYLOAD] json dump failed: %s", e)
        payload_json = "{}"

    text = f"{prompt}\n\n[입력]\n{payload_json}"
    log.info("[LLM] request start")

    out = request_llm(text)

    if not out:
        log.error("[LLM] empty response")
        log.info("========== [LLM ATTRIBUTE RESOLVE END - ERROR] ==========")
        return {"error": "empty_response", "raw": out}

    log.info("[LLM] raw_len=%d", len(out))
    log.debug("[LLM RAW PREVIEW]\n%s", out[:PREVIEW_LIMIT])

    # -------------------------------------------------
    # 4) JSON 파싱 (```json ... ``` 제거 포함)
    # -------------------------------------------------
    cleaned = _extract_json(out)
    log.debug("[LLM CLEANED PREVIEW]\n%s", cleaned[:PREVIEW_LIMIT])

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("parsed json is not a dict")
    except Exception as e:
        log.error("[LLM] JSON parse failed: %s", e)
        log.error("[LLM RAW]\n%s", out)
        log.error("[LLM CLEANED]\n%s", cleaned)
        log.info("========== [LLM ATTRIBUTE RESOLVE END - ERROR] ==========")
        return {"error": "invalid_json", "raw": out, "cleaned": cleaned}

    raw_selections = parsed.get("selections", {}) or {}
    raw_selections = _normalize_selections_keys(raw_selections)

    # 🔥 핵심 추가: attributeName → caid 정규화
    selections = normalize_selections_to_caid(
        raw_selections,
        attrs,   # payload["attributes"]
    )

    parsed["selections"] = selections

    reason = parsed.get("reason")

    log.info("[LLM] parsed OK | selections=%d", len(selections))
    if reason:
        log.info("[LLM] reason: %s", _one_line(reason))

    # -------------------------------------------------
    # 5) 사람용 상세 로그: 후보군 + RULE/LLM HIT 마킹
    # -------------------------------------------------
    log.info("---------- [LLM PICK DETAIL] ----------")

    for a in attrs:
        caid = str(a.get("categoryAttributeId"))
        name = str(a.get("attributeName") or "")
        ctype = str(a.get("classificationType") or "")

        rule_value_seqs = a.get("currentPickedValueSeqs") or []
        rule_text = a.get("currentPickedText")

        # 후보군 먼저 확보 (★ 가장 중요)
        values = a.get("attributeValues") or []
        idx = _build_value_index(values)

        llm_pick_raw = selections.get(caid, None)

        mapped = _map_llm_pick_to_seqs(
            llm_pick_raw,
            values,
            ctype,
        )

        # LLM 결과를 seq로 교체
        if mapped is not None:
            selections[caid] = mapped

        idx = _build_value_index(values)

        log.info("[ATTR] %s | %s | categoryAttributeId=%s", name, ctype, caid)

        # RULE 결과를 사람이 읽게(seq->명)로
        if ctype in ("SINGLE_SELECT", "MULTI_SELECT"):
            log.info("  - rule : %s", _format_seqs(rule_value_seqs, idx))
        else:
            log.info("  - rule : %s", _fmt_text(rule_text))

        # LLM 결과를 사람이 읽게
        if llm_pick_raw is None:
            log.info("  - llm  : MISS")
        else:
            log.info("  - llm  : PICK %s", _format_llm_pick(llm_pick_raw, ctype, idx))

        # 후보군 출력 (요구하신 핵심)
        if ctype in ("SINGLE_SELECT", "MULTI_SELECT"):
            _log_candidates(values, idx, rule_value_seqs, llm_pick_raw, ctype)
        else:
            # TEXT면 후보군이 없을 수도 있음
            if values:
                _log_candidates(values, idx, rule_value_seqs, llm_pick_raw, ctype)

    log.info("========== [LLM ATTRIBUTE RESOLVE END] ==========")
    return parsed


def build_llm_attribute_payload(payload: dict) -> dict:
    out = {
        "product_name": payload.get("product_name"),
        "option_names": payload.get("option_names"),
        "detail_text": payload.get("detail_text"),
        "attributes": [],
    }

    for a in payload.get("attributes", []):
        ctype = a.get("classificationType")
        max_cnt = a.get("maxMatchingCount")

        # TEXT는 LLM 대상 아님
        if ctype == "TEXT":
            continue

        # 선택 가능 개수 확정
        if ctype == "SINGLE_SELECT":
            pick_limit = 1
        elif ctype == "MULTI_SELECT":
            pick_limit = max_cnt or 1
        else:
            continue

        candidates = []
        for v in a.get("attributeValues", []):
            seq = v.get("attributeValueSeq")
            text = v.get("attributeValueText")
            if seq and text:
                candidates.append({"seq": seq, "text": text})

        if not candidates:
            continue

        out["attributes"].append({
            "categoryAttributeId": a["categoryAttributeId"],
            "classificationType": ctype,
            "pick_limit": pick_limit,   # 🔥 이게 핵심
            "candidates": candidates,
        })

    return out



# ---------------------------
# Candidate logging helpers
# ---------------------------
def _log_candidates(
    values: List[dict],
    idx: Dict[int, str],
    rule_seqs: List[int],
    llm_pick_raw: Any,
    ctype: str,
):
    rule_set = set(_safe_int_list(rule_seqs))

    llm_set: set[int] = set()
    if ctype == "SINGLE_SELECT":
        if isinstance(llm_pick_raw, int):
            llm_set = {llm_pick_raw}
        elif isinstance(llm_pick_raw, list):
            llm_set = set(_safe_int_list(llm_pick_raw)[:1])
    elif ctype == "MULTI_SELECT":
        if isinstance(llm_pick_raw, list):
            llm_set = set(_safe_int_list(llm_pick_raw))
        elif isinstance(llm_pick_raw, int):
            llm_set = {llm_pick_raw}

    log.info("  - candidates:")

    for v in values:
        seq = _safe_int(v.get("attributeValueSeq"))
        label = (
            v.get("attributeValueText")
            or v.get("attributeValueName")
            or v.get("minAttributeValue")
            or ""
        )
        label = str(label).strip()

        if seq is None:
            continue

        tags = []
        if seq in rule_set:
            tags.append("RULE")
        if seq in llm_set:
            tags.append("LLM")

        tag = f" [{'|'.join(tags)}]" if tags else ""
        log.info("    - %s (%s)%s", label, seq, tag)


# ---------------------------
# Utils
# ---------------------------
import re

def _extract_json(text: str) -> str:
    """
    - ```json ... ``` / ``` ... ``` 제거
    - //, /* */ 주석 제거
    - 첫 { 부터 마지막 } 까지만 추출
    """
    if not text:
        return ""

    t = text.strip()

    # ```json ... ``` 제거
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 2:
            t = parts[1].strip()

            # "json\n{...}" 형태면 첫 줄 제거
            if t.lower().startswith("json"):
                t = t.split("\n", 1)[-1].strip()

    # 🔥 핵심 추가 1: // 한 줄 주석 제거
    t = re.sub(r"//.*", "", t)

    # 🔥 핵심 추가 2: /* 여러 줄 주석 */ 제거
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.DOTALL)

    # JSON 영역만 추출
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and start < end:
        return t[start:end + 1]

    return t


def normalize_selections_to_caid(
    selections: Dict[str, Any],
    attributes: List[dict],
) -> Dict[str, Any]:
    """
    LLM selections의 key를
    - categoryAttributeId(str) 기준으로 통일
    - attributeName으로 온 경우 caid로 변환
    """

    # attributeName -> caid(str) 매핑
    name_to_caid: Dict[str, str] = {}
    for a in attributes or []:
        caid = a.get("categoryAttributeId")
        name = a.get("attributeName")
        if caid is not None and name:
            name_to_caid[str(name).strip()] = str(caid)

    normalized: Dict[str, Any] = {}

    for k, v in selections.items():
        ks = str(k).strip()

        # 1️⃣ 이미 caid면 그대로
        if ks.isdigit():
            normalized[ks] = v
            continue

        # 2️⃣ attributeName이면 caid로 변환
        caid = name_to_caid.get(ks)
        if caid:
            normalized[caid] = v
            continue

        # 3️⃣ 알 수 없는 키는 로그만 남기고 버림
        log.warning(
            "[LLM][SELECTION DROP] unknown key='%s' (cannot map to caid)",
            ks,
        )

    return normalized



def _pretty(obj: Any, limit: int = 4000) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, indent=2)
        if len(s) > limit:
            return s[:limit] + "\n... (truncated)"
        return s
    except Exception:
        return str(obj)


def _build_value_index(values: List[dict]) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for v in values or []:
        seq = _safe_int(v.get("attributeValueSeq"))
        name = v.get("attributeValueName")
        if seq is not None and isinstance(name, str) and name.strip():
            out[seq] = name.strip()
    return out


def _safe_int(x) -> Optional[int]:
    try:
        if x is None:
            return None
        return int(x)
    except Exception:
        return None


def _safe_int_list(xs) -> List[int]:
    out: List[int] = []
    if not isinstance(xs, list):
        return out
    for x in xs:
        xi = _safe_int(x)
        if xi is not None:
            out.append(xi)
    return out


def _format_seqs(seqs: List[int], idx: Dict[int, str]) -> str:
    seqs = _safe_int_list(seqs)
    if not seqs:
        return "MISS"
    pairs = [f"{s}:{_clean(idx.get(s, ''))}" for s in seqs]
    return "[" + ", ".join(pairs) + "]"


def _format_llm_pick(v: Any, ctype: str, idx: Dict[int, str]) -> str:
    if v is None:
        return "MISS"

    if ctype == "SINGLE_SELECT":
        if isinstance(v, int):
            return _format_seqs([v], idx)
        if isinstance(v, list):
            return _format_seqs(_safe_int_list(v)[:1], idx)
        return str(v)

    if ctype == "MULTI_SELECT":
        if isinstance(v, int):
            return _format_seqs([v], idx)
        if isinstance(v, list):
            return _format_seqs(_safe_int_list(v), idx)
        return str(v)

    # TEXT
    if isinstance(v, str):
        return _fmt_text(v)
    return str(v)


def _fmt_text(s: Any) -> str:
    if not isinstance(s, str):
        return "MISS"
    s = s.strip()
    return s if s else "MISS"


def _fmt_rule_pick(a: dict) -> str:
    ctype = str(a.get("classificationType") or "")
    if ctype in ("SINGLE_SELECT", "MULTI_SELECT"):
        return str(a.get("currentPickedValueSeqs") or "MISS")
    return _fmt_text(a.get("currentPickedText"))


def _one_line(s: str) -> str:
    return " ".join(str(s).split())


def _clean(s: str) -> str:
    return " ".join(str(s).split())

def _map_llm_pick_to_seqs(
    llm_pick_raw: Any,
    values: List[dict],
    ctype: str,
) -> Union[int, List[int], None]:
    """
    LLM이 텍스트로 고른 값을 attributeValueSeq로 변환
    """
    if llm_pick_raw is None:
        return None

    # 후보 label → seq 매핑
    label_to_seq = {}
    for v in values or []:
        seq = _safe_int(v.get("attributeValueSeq"))
        label = (
            v.get("attributeValueText")
            or v.get("attributeValueName")
            or ""
        )
        if seq and isinstance(label, str):
            label_to_seq[label.strip()] = seq

    def find_seq(text: str) -> Optional[int]:
        text = text.strip()
        for label, seq in label_to_seq.items():
            # 부분 일치 허용 (폴리에스터 vs 폴리에스테르 대응)
            if text == label or text in label or label in text:
                return seq
        return None

    if ctype == "SINGLE_SELECT":
        if isinstance(llm_pick_raw, str):
            return find_seq(llm_pick_raw)
        if isinstance(llm_pick_raw, int):
            return llm_pick_raw

    if ctype == "MULTI_SELECT":
        out = []
        if isinstance(llm_pick_raw, list):
            for x in llm_pick_raw:
                if isinstance(x, str):
                    s = find_seq(x)
                    if s:
                        out.append(s)
                elif isinstance(x, int):
                    out.append(x)
        elif isinstance(llm_pick_raw, str):
            s = find_seq(llm_pick_raw)
            if s:
                out.append(s)
        return out or None

    # TEXT 타입
    return llm_pick_raw

def _normalize_selections_keys(raw: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(raw, dict):
        return out

    for k, v in raw.items():
        if k is None:
            continue
        ks = str(k).strip()
        if not ks:
            continue
        out[ks] = v
    return out

