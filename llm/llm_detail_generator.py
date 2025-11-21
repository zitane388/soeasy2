# llm_detail_generator.py

import json
from llm.llm_client import request_llm
from llm.llm_formatter import DETAIL_DESCRIPTION_PROMPT

def generate_sections_from_llm(original_text: str) -> dict:
    if not original_text:
        return {}

    prompt = DETAIL_DESCRIPTION_PROMPT.replace("{INPUT_TEXT}", original_text)

    raw = request_llm(prompt)

    return raw.strip()
