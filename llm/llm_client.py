# llm_client.py
# Soeasy2 LLM 요청 전용 모듈 (프롬프트 일원화 + split 구조)

import json
import time
import os
import base64
import importlib
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# -----------------------------------------------------
# 1) API 설정
# -----------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = "gpt-4o-mini"
TIMEOUT = 45
RETRY = 2

if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
    raise RuntimeError(
        "환경변수 OPENAI_API_KEY가 설정되지 않았습니다.\n"
        ".env 파일에 유효한 OpenAI API 키를 설정해주세요.\n"
        "https://platform.openai.com/api-keys"
    )

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
        "CATEGORY_FALLBACK": formatter_module.CATEGORY_PICK_PROMPT,
        "CATEGORY_DETAIL_FILTER": formatter_module.CATEGORY_DETAIL_FILTER_PROMPT,
        "ATTRIBUTE_PICK": formatter_module.ATTRIBUTE_PICK_PROMPT,
        "CAPTCHA": formatter_module.CAPTCHA_SOLVE_PROMPT,
        "PRODUCT_OPTION_GROUP_FILTER_PROMPT": formatter_module.PRODUCT_OPTION_GROUP_FILTER_PROMPT
    }

# 최초 초기화
PROMPTS = {}
reload_formatter()

def get_prompt(name: str) -> str:
    """외부 모듈에서 항상 최신 프롬프트를 가져가는 통일된 방식"""
    return PROMPTS.get(name, "")

# -----------------------------------------------------
# 3) 단일 프롬프트 LLM 요청 (기존 방식 유지)
# -----------------------------------------------------
def request_llm(prompt: str) -> str:
    for attempt in range(RETRY + 1):
        try:
            response = client.responses.create(
                model=LLM_MODEL,
                input=prompt
            )

            if hasattr(response, "output_text") and response.output_text:
                return response.output_text.strip()

            try:
                return response.data[0].content[0].text.strip()
            except Exception:
                pass

            raise RuntimeError("LLM 응답에서 텍스트 추출 실패")

        except Exception as e:
            print(f"[LLM] 실패 {attempt+1}/{RETRY+1} → {e}")
            time.sleep(1.2)

    print("[LLM] 최종 실패")
    return ""

# -----------------------------------------------------
# 4) 이미지 포함 LLM 요청
# -----------------------------------------------------
def request_llm_with_image(prompt: str, image_url: str) -> str:
    for attempt in range(RETRY + 1):
        try:
            response = client.responses.create(
                model=LLM_MODEL,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": image_url},
                        ],
                    }
                ],
            )

            if hasattr(response, "output_text") and response.output_text:
                return response.output_text.strip()

            try:
                return response.data[0].content[0].text.strip()
            except Exception:
                pass

            raise RuntimeError("Vision LLM 응답 텍스트 추출 실패")

        except Exception as e:
            print(f"[LLM-IMG] 실패 {attempt+1}/{RETRY+1} → {e}")
            time.sleep(1.2)

    print("[LLM-IMG] 최종 실패")
    return ""

# -----------------------------------------------------
# 5) Prefix / Suffix 분리 요청 (Prompt Caching 대응)
# -----------------------------------------------------
def request_llm_split(prefix: str, suffix: str) -> str:
    for attempt in range(RETRY + 1):
        try:
            response = client.responses.create(
                model=LLM_MODEL,
                input=[
                    {"role": "system", "content": prefix},
                    {"role": "user", "content": suffix},
                ],
            )

            if hasattr(response, "output_text") and response.output_text:
                return response.output_text.strip()

            try:
                return response.data[0].content[0].text.strip()
            except Exception:
                pass

            raise RuntimeError("LLM 응답에서 텍스트 추출 실패")

        except Exception as e:
            print(f"[LLM-SPLIT] 실패 {attempt+1}/{RETRY+1} → {e}")
            time.sleep(1.2)

    print("[LLM-SPLIT] 최종 실패")
    return ""

# -----------------------------------------------------
# 6) 간단 캐시 (split용 확장 가능)
# -----------------------------------------------------
_cache = {}

def request_llm_split_cached(prefix_id: str, prefix: str, suffix: str) -> str:
    cache_key = f"{LLM_MODEL}:{prefix_id}:{hash(suffix)}"

    if cache_key in _cache:
        return _cache[cache_key]

    out = request_llm_split(prefix, suffix)
    _cache[cache_key] = out
    return out