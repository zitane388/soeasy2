# product_name_llm.py

import hashlib
from llm.llm_client import request_llm
from llm.llm_formatter import PRODUCT_NAME_PROMPT


def make_cache_key(url, primary_keywords, secondary_keywords):
    raw = url + " ".join(primary_keywords) + " ".join(secondary_keywords)
    return "PNAME_" + hashlib.md5(raw.encode()).hexdigest()


def generate_product_name_from_llm(primary_keywords, secondary_keywords):
    # 키워드 준비
    p_kw = ", ".join(primary_keywords) if primary_keywords else ""
    s_kw = ", ".join(secondary_keywords) if secondary_keywords else ""

    prompt = PRODUCT_NAME_PROMPT.format(
        P_KEYWORDS=p_kw,
        S_KEYWORDS=s_kw
    )

    return request_llm(prompt)
