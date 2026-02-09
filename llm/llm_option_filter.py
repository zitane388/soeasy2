# llm_option_filter.py

import json, re
from llm.llm_client import get_prompt, request_llm


def _extract_json(text: str) -> str:
    text = text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)

    return text.strip()


def pick_option_groups_by_llm(
    option_groups: dict,
    hint_keywords: list[str],
    product_title: str = ""
) -> list[str]:
    prompt_template = get_prompt("PRODUCT_OPTION_GROUP_FILTER_PROMPT")

    prompt = prompt_template.format(
        product_title=product_title,
        option_groups=json.dumps(option_groups, ensure_ascii=False, indent=2),
        hint_keywords=", ".join(hint_keywords),
    )

    raw = request_llm(prompt)
    if not raw:
        return []

    try:
        cleaned = _extract_json(raw)
        parsed = json.loads(cleaned)
        return parsed.get("option_groups", [])
    except Exception as e:
        print("[LLM OPTION FILTER] JSON 파싱 실패")
        print(cleaned)
        print(e)
        return []
