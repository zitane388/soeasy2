from __future__ import annotations

import copy
import json
import re
import threading
import unicodedata
from pathlib import Path

from utils.path import p


GROUP_COLOR_KO = "\uc0c9\uc0c1"
GROUP_SIZE_KO = "\uc0ac\uc774\uc988"

_MAPPING_PATH = Path(p("templates", "option_mapping.json"))
_LOCK = threading.Lock()
_GROUP_KEY_PREFIX = "group::"
_VALUE_KEY_PREFIX = "value::"
_AUTO_PERSIST_MAPPING = False

_UNIT_PATTERN = re.compile(
    r"(?i)\b(\d+(?:\.\d+)?)\s*(mm|cm|m|ml|l|g|kg|oz|inch|in|ea|pcs|pc|set)\b"
)
_SHOE_SIZE_PATTERN = re.compile(r"^(?:size\s*)?(\d{2})\.(\d)$", re.IGNORECASE)
_GROUP_PREFIX_PATTERN = re.compile(
    r"^\s*\[?\s*group\s*=\s*[^\]]+\]?\s*",
    re.IGNORECASE,
)


def _default_mapping() -> dict:
    return {}


def _normalize_text(value: str) -> str:
    if not isinstance(value, str):
        return value
    text = unicodedata.normalize("NFKC", value)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_key(text: str) -> str:
    return _normalize_text(text or "").lower()


def _normalize_number_unit(value: str) -> str:
    text = _normalize_text(value)
    text = _UNIT_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2).lower()}", text)
    text = text.replace(" 횞 ", " x ").replace("횞", " x ")
    text = re.sub(r"\s*x\s*", " x ", text)
    return _normalize_text(text)


def _normalize_korean_size_value(value: str) -> str:
    text = _normalize_number_unit(value)
    m = _SHOE_SIZE_PATTERN.match(text)
    if not m:
        return text
    integer = int(m.group(1))
    decimal = int(m.group(2))
    if 20 <= integer <= 35 and decimal in (0, 5):
        return str(integer * 10 + decimal)
    return text


def _contains_korean(text: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7a3]", text or ""))


def _looks_like_code_or_model(text: str) -> bool:
    t = _normalize_text(text)
    if not t:
        return False
    if re.fullmatch(r"[A-Z0-9][A-Z0-9\-_/.]{3,}", t, flags=re.IGNORECASE):
        has_alpha = bool(re.search(r"[A-Z]", t, flags=re.IGNORECASE))
        has_digit = bool(re.search(r"\d", t))
        return has_alpha and has_digit
    return False


def _needs_llm_translation(text: str) -> bool:
    if not text:
        return False
    if _contains_korean(text):
        return False
    if _looks_like_code_or_model(text):
        return False
    return True


def _merge_simple(flat: dict[str, str], raw_key: str, value: str) -> None:
    key = _normalize_key(raw_key)
    val = _normalize_text(value)
    if key and val and key not in flat:
        flat[key] = val


def _flatten_legacy_mapping(data: dict) -> dict:
    flat: dict[str, str] = {}

    for raw_group, translated_group in (data.get("group_name_map") or {}).items():
        if isinstance(raw_group, str) and isinstance(translated_group, str):
            _merge_simple(flat, raw_group, translated_group)

    for _, group_values in (data.get("value_map") or {}).items():
        if not isinstance(group_values, dict):
            continue
        for raw_value, translated_value in group_values.items():
            if isinstance(raw_value, str) and isinstance(translated_value, str):
                _merge_simple(flat, raw_value, translated_value)

    return flat


def _flatten_prefixed_mapping(data: dict) -> dict:
    flat: dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue

        if k.startswith(_GROUP_KEY_PREFIX):
            _merge_simple(flat, k[len(_GROUP_KEY_PREFIX) :], v)
            continue

        if k.startswith(_VALUE_KEY_PREFIX):
            body = k[len(_VALUE_KEY_PREFIX) :]
            if "::" in body:
                _, raw_value = body.rsplit("::", 1)
            else:
                raw_value = body
            _merge_simple(flat, raw_value, v)
            continue

        _merge_simple(flat, k, v)

    return flat


def _load_mapping() -> dict:
    if not _MAPPING_PATH.exists():
        return _default_mapping()
    try:
        data = json.loads(_MAPPING_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_mapping()

        if "group_name_map" in data or "value_map" in data:
            return _flatten_legacy_mapping(data)

        return _flatten_prefixed_mapping(data)
    except Exception:
        return _default_mapping()


def _save_mapping(data: dict) -> None:
    if not _AUTO_PERSIST_MAPPING:
        return
    _MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MAPPING_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_group_name_mapped(raw_group_name: str) -> str | None:
    key = _normalize_key(raw_group_name)
    if not key:
        return None
    with _LOCK:
        mapping = _load_mapping()
        out = mapping.get(key)
        return _normalize_text(out) if isinstance(out, str) and out.strip() else None


def _remember_group_name(raw_group_name: str, translated_group_name: str) -> None:
    if not _AUTO_PERSIST_MAPPING:
        return
    raw_key = _normalize_key(raw_group_name)
    val = _normalize_text(translated_group_name)
    if not raw_key or not val:
        return
    with _LOCK:
        mapping = _load_mapping()
        mapping[raw_key] = val
        _save_mapping(mapping)


def _get_value_mapped(group_name: str, raw_value: str) -> str | None:
    _ = group_name
    key = _normalize_key(raw_value)
    if not key:
        return None
    with _LOCK:
        mapping = _load_mapping()
        out = mapping.get(key)
        return _normalize_text(out) if isinstance(out, str) and out.strip() else None


def _remember_value(group_name: str, raw_value: str, translated_value: str) -> None:
    if not _AUTO_PERSIST_MAPPING:
        return
    _ = group_name
    raw_key = _normalize_key(raw_value)
    val = _normalize_text(translated_value)
    if not raw_key or not val:
        return
    with _LOCK:
        mapping = _load_mapping()
        mapping[raw_key] = val
        _save_mapping(mapping)


def _translate_option_value_via_llm(value: str, group_name: str) -> str:
    try:
        from llm.llm_option_translator import translate_option_value_llm

        return translate_option_value_llm(value, group_name=group_name)
    except Exception as e:
        print(f"[OptionTranslator] value LLM import/call failed: {e}")
        return value


def _translate_option_group_name_via_llm(group_name: str, option_values: list[str]) -> str:
    try:
        from llm.llm_option_translator import translate_option_group_name_llm

        return translate_option_group_name_llm(group_name, option_values or [])
    except Exception as e:
        print(f"[OptionTranslator] group LLM import/call failed: {e}")
        return group_name


def _normalize_group_name(group_name: str, option_values: list[str] | None = None) -> str:
    raw = _normalize_text(group_name or "")
    if not raw:
        return raw

    mapped = _get_group_name_mapped(raw)
    if mapped:
        return mapped

    translated = _normalize_text(
        _translate_option_group_name_via_llm(raw, option_values or []) or raw
    )
    if translated:
        _remember_group_name(raw, translated)
    return translated or raw


def _translate_value(value: str, group_name: str) -> str:
    raw = _normalize_text(value)
    raw = _GROUP_PREFIX_PATTERN.sub("", raw)
    if not raw:
        return raw

    mapped = _get_value_mapped(group_name, raw)
    if mapped:
        return mapped

    normalized = (
        _normalize_korean_size_value(raw)
        if group_name == GROUP_SIZE_KO
        else _normalize_number_unit(raw)
    )

    if not _needs_llm_translation(normalized):
        _remember_value(group_name, raw, normalized)
        return normalized

    translated = _normalize_text(
        _translate_option_value_via_llm(normalized, group_name=group_name) or normalized
    )
    translated = _GROUP_PREFIX_PATTERN.sub("", translated)

    out = (
        _normalize_korean_size_value(translated)
        if group_name == GROUP_SIZE_KO
        else _normalize_number_unit(translated)
    )
    _remember_value(group_name, raw, out)
    return out


def translate_option_groups(option_groups: list[dict]) -> list[dict]:
    if not isinstance(option_groups, list):
        return option_groups

    translated_groups: list[dict] = []
    for group in option_groups:
        if not isinstance(group, dict):
            translated_groups.append(group)
            continue

        new_group = copy.deepcopy(group)
        raw_group_name = new_group.get("group_name_original") or new_group.get("group_name", "")
        if "group_name_original" not in new_group:
            new_group["group_name_original"] = raw_group_name
        raw_values = new_group.get("values", [])
        sample_values = []
        if isinstance(raw_values, list):
            for value in raw_values:
                if isinstance(value, dict):
                    name = value.get("name_original") or value.get("name")
                    if isinstance(name, str) and name.strip():
                        sample_values.append(name.strip())

        normalized_group_name = _normalize_group_name(raw_group_name, sample_values)
        new_group["group_name"] = normalized_group_name

        values = new_group.get("values", [])
        if not isinstance(values, list):
            translated_groups.append(new_group)
            continue

        for value_obj in values:
            if not isinstance(value_obj, dict):
                continue
            raw_name = value_obj.get("name_original") or value_obj.get("name", "")
            if "name_original" not in value_obj:
                value_obj["name_original"] = raw_name
            value_obj["name"] = _translate_value(raw_name, normalized_group_name)

        translated_groups.append(new_group)

    return translated_groups

