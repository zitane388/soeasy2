# llm_client.py
# Soeasy2 LLM 요청 전용 모듈 (프롬프트 일원화 버전)

import json, time, os, base64
import importlib
from openai import OpenAI

# -----------------------------------------------------
# 1) API 설정
# -----------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")   # <-- 환경변수로 변경
LLM_MODEL = "gpt-4o-mini"
TIMEOUT = 45
RETRY = 2

if not OPENAI_API_KEY:
    raise RuntimeError("환경변수 OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY, timeout=TIMEOUT)

# -----------------------------------------------------
# 2) 프롬프트 중앙관리
# -----------------------------------------------------
from llm import llm_formatter as formatter_module

def reload_formatter():
    """GUI 편집기에서 저장 시 호출됨"""
    global formatter_module, PROMPTS
    importlib.reload(formatter_module)

    PROMPTS = {
        "DETAIL": formatter_module.DETAIL_DESCRIPTION_PROMPT,
        "OPTION": formatter_module.PRODUCT_OPTION_PROMPT,
        "NAME": formatter_module.PRODUCT_NAME_PROMPT,
        "NAME_VISION": formatter_module.PRODUCT_NAME_PROMPT_VISION,

        # 카테고리 관련 2종
        "CATEGORY_MID": formatter_module.CATEGORY_MID_SELECT_PROMPT,
        "CATEGORY_FINAL": formatter_module.CATEGORY_FINAL_SELECT_PROMPT,
    }


# 최초 초기화
PROMPTS = {}
reload_formatter()

def get_prompt(name: str) -> str:
    """외부 모듈에서 항상 최신 프롬프트를 가져가는 통일된 방식"""
    return PROMPTS.get(name, "")

# -----------------------------------------------------
# 3) LLM 요청 함수
# -----------------------------------------------------
def request_llm(prompt: str) -> str:
    last_err = None

    for attempt in range(RETRY + 1):
        try:
            response = client.responses.create(
                model=LLM_MODEL,
                input=prompt
            )

            if hasattr(response, "output_text") and response.output_text:
                return response.output_text.strip()

            try:
                text = response.data[0].content[0].text
                return text.strip()
            except:
                pass

            raise RuntimeError("LLM 응답에서 텍스트 추출 실패")

        except Exception as e:
            last_err = e
            print(f"[LLM] 실패 {attempt+1}/{RETRY+1} → {e}")
            time.sleep(1.2)

    print("[LLM] 최종 실패, prompt 일부 반환")
    return prompt[:200]

# -----------------------------------------------------
# 5) 이미지 포함 LLM 요청 함수 (신규)
# -----------------------------------------------------
# llm_client.py

def request_llm_with_image(prompt: str, image_url: str) -> str:
    last_err = None

    for attempt in range(RETRY + 1):
        try:
            response = client.responses.create(
                model=LLM_MODEL,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text",  "text": prompt},
                            {"type": "input_image", "image_url": image_url}   # 🔥 dict 아님
                        ]
                    }
                ]
            )

            if hasattr(response, "output_text"):
                return response.output_text.strip()

            try:
                return response.data[0].content[0].text.strip()
            except:
                pass

            raise RuntimeError("LLM 응답 텍스트 추출 실패")

        except Exception as e:
            print(f"[LLM-IMG] 실패 {attempt+1}/{RETRY+1} → {e}")
            last_err = e

    print("[LLM-IMG] 최종 실패 → Vision 응답 없음")
    return ""



# -----------------------------------------------------
# 4) 캐시 기능
# -----------------------------------------------------
_cache = {}

def request_llm_cached(key: str, prompt: str) -> str:
    if key in _cache:
        return _cache[key]
    out = request_llm(prompt)
    _cache[key] = out
    return out
