# llm_detail_generator.py

from llm.llm_client import request_llm, get_prompt

def generate_sections_from_llm(original_text: str) -> dict:
    if not original_text:
        return {}

    prompt = get_prompt("DETAIL").replace("{INPUT_TEXT}", original_text)

    raw = request_llm(prompt)

    return raw.strip()
