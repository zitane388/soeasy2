# llm/llm_option_translator.py

from llm.llm_client import request_llm, get_prompt

def translate_option_value_llm(value: str) -> str:
    """
    옵션명 하나를 LLM에 보내 자연스러운 한국어로 번역하여 반환한다.
    """
    prompt = get_prompt("OPTION").format(OPTION_NAME=value)

    try:
        out = request_llm(prompt)
        return out.strip().replace('"', "").replace("'", "")
    except Exception as e:
        print(f"[LLM Option] 번역 실패: {e}")
        return value
