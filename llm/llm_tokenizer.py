import json
import hashlib
import logging
import re
from typing import List, Optional

from llm.llm_client import request_llm_cached, get_prompt


log = logging.getLogger(__name__)


class LLMTokenizer:
    """
    LLM을 이용한 '토큰 분리 전용' 모듈

    - 의미 판단 ❌
    - 분류 ❌
    - 추론 ❌
    - 원문 단어/구 보존
    """

    # ==========================================================
    # public API
    # ==========================================================
    def tokenize(self, texts: List[str]) -> List[str]:
        joined = " ".join(t for t in texts if t).strip()

        log.info(
            "[LLMTokenizer] tokenize start | texts=%s",
            texts
        )

        if not joined:
            log.warning("[LLMTokenizer] empty input → skip")
            return []

        prompt_template = get_prompt("CATEGORY_TOKENIZE")
        if not prompt_template:
            log.error("[LLMTokenizer] CATEGORY_TOKENIZE prompt not found")
            return []

        prompt = prompt_template.format(INPUT_TEXT=joined)

        # 캐시 키 (입력 문자열 기준)
        key = "tokenize:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()

        log.debug(
            "[LLMTokenizer] request LLM | cache_key=%s input='%s'",
            key[:12],
            joined
        )

        resp = request_llm_cached(key, prompt)

        log.debug(
            "[LLMTokenizer] raw LLM response | %s",
            resp
        )

        # ------------------------------------------------------
        # JSON 추출
        # ------------------------------------------------------
        json_text = self._extract_json_array(resp)
        if not json_text:
            log.warning(
                "[LLMTokenizer] no JSON array found in response | resp=%s",
                resp
            )
            return []

        try:
            tokens = json.loads(json_text)

            if not isinstance(tokens, list):
                log.warning(
                    "[LLMTokenizer] JSON parsed but not list | type=%s",
                    type(tokens)
                )
                return []

            final_tokens = [
                t.strip()
                for t in tokens
                if isinstance(t, str) and len(t.strip()) >= 2
            ]

            log.info(
                "[LLMTokenizer] tokenize success | tokens=%s",
                final_tokens
            )

            return final_tokens

        except Exception as e:
            log.warning(
                "[LLMTokenizer] JSON parse failed | error=%s | json_text=%s",
                e,
                json_text
            )
            return []

    # ==========================================================
    # internal utils
    # ==========================================================
    @staticmethod
    def _extract_json_array(text: str) -> Optional[str]:
        """
        LLM 응답에서 JSON 배열 부분만 안전하게 추출

        허용 예:
        - ["a", "b"]
        - ```json\n["a","b"]\n```
        - ```\n["a","b"]\n```
        """

        if not text:
            return None

        # 가장 단순하고 안전한 방식:
        # 첫 '[' 부터 마지막 ']' 까지
        match = re.search(r"\[[\s\S]*?\]", text)
        if not match:
            return None

        return match.group(0)
