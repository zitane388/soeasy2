import json
import re

from llm.llm_client import get_prompt, request_llm


_LABEL_PREFIX_PATTERN = re.compile(
    r"^(?:value|result|translation|translated)\s*[:\-]\s*",
    re.IGNORECASE,
)
_GROUP_PREFIX_PATTERN = re.compile(
    r"^\s*\[?\s*group\s*=\s*[^\]]+\]?\s*",
    re.IGNORECASE,
)
_GROUP_LABEL_PREFIX_PATTERN = re.compile(
    r"^(?:group_name|group|label|name)\s*[:\-]\s*",
    re.IGNORECASE,
)


def _clean_llm_output(raw: str, fallback: str) -> str:
    text = (raw or "").strip()
    if not text:
        return fallback

    text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
            v = obj.get("value")
            if isinstance(v, str) and v.strip():
                text = v.strip()
        except Exception:
            pass

    line = text.splitlines()[0].strip() if text.splitlines() else text
    line = _LABEL_PREFIX_PATTERN.sub("", line)
    line = _GROUP_PREFIX_PATTERN.sub("", line)
    line = line.strip().strip("\"'").strip()
    return line or fallback


def _clean_group_name_output(raw: str, fallback: str) -> str:
    text = (raw or "").strip()
    if not text:
        return fallback

    text = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
            v = obj.get("group_name")
            if isinstance(v, str) and v.strip():
                text = v.strip()
        except Exception:
            pass

    line = text.splitlines()[0].strip() if text.splitlines() else text
    line = _GROUP_LABEL_PREFIX_PATTERN.sub("", line)
    line = line.strip().strip("\"'").strip()
    return line or fallback


def translate_option_value_llm(value: str, group_name: str = "") -> str:
    if not isinstance(value, str) or not value.strip():
        return value

    template = get_prompt("OPTION") or ""
    group_label = (group_name or "option").strip()

    if "{GROUP_NAME}" in template:
        prompt = template.format(GROUP_NAME=group_label, OPTION_NAME=value)
    elif "{OPTION_NAME}" in template and template.strip():
        prompt = template.format(OPTION_NAME=value)
    else:
        prompt = f"{group_label}: {value}"

    try:
        out = request_llm(prompt)
        return _clean_llm_output(out, value)
    except Exception as e:
        print(f"[LLM Option] translation failed: {e}")
        return value


def translate_option_group_name_llm(group_name: str, option_values: list[str] | None = None) -> str:
    raw_group = (group_name or "").strip()
    if not raw_group:
        return raw_group

    values = [str(v).strip() for v in (option_values or []) if str(v).strip()]
    sample = ", ".join(values[:10])

    template = get_prompt("OPTION_GROUP_NAME") or ""
    if "{GROUP_NAME}" in template and "{OPTION_VALUES}" in template:
        prompt = template.format(GROUP_NAME=raw_group, OPTION_VALUES=sample)
    else:
        prompt = (
            "Translate one option group label into Korean shopping wording.\n"
            f"Raw group label: {raw_group}\n"
            f"Sample option values: {sample}\n"
            "Output JSON one-line only: {\"group_name\":\"...\"}"
        )

    try:
        out = request_llm(prompt)
        return _clean_group_name_output(out, raw_group)
    except Exception as e:
        print(f"[LLM Option Group] translation failed: {e}")
        return raw_group
