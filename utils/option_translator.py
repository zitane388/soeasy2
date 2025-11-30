import re
from llm.llm_option_translator import translate_option_value_llm

SIZE_KEYWORDS = {"xxs","xs","s","m","l","xl","xxl","xxxl","xxxxl"}

SIZE_NUMERIC_PATTERN = r"^\d+\s*(xs|s|m|l|xl|xxl|xxxl|xxxxl)$"

UNIT_PATTERNS = [
    r"^\d+(\.\d+)?(cm|mm|inch|in|kg|g)$",
    r"^\d+(\.\d+)?$"
]


def is_numeric_or_unit(text: str):
    t = text.lower().strip()

    for p in UNIT_PATTERNS:
        if re.match(p, t):
            return True

    if t in SIZE_KEYWORDS:
        return True

    if re.match(SIZE_NUMERIC_PATTERN, t):
        return True

    return False


def needs_translation(text: str):
    t = text.strip()
    if not t:
        return False

    if is_numeric_or_unit(t):
        return False

    # 일본어 / 중국어
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", t):
        return True

    # 영어 단어
    if re.search(r"[a-zA-Z]", t):
        return True

    return False


# ------------------------------------------------------------
# 2) 옵션 그룹 번역 + 로그 출력
# ------------------------------------------------------------
def translate_option_groups(option_groups):
    new_groups = []

    for group in option_groups:
        new_vals = []

        for v in group["values"]:
            name = v["name"]

            if needs_translation(name):
                translated = translate_option_value_llm(name)
            else:
                translated = name

            new_vals.append({
                **v,
                "name": translated
            })

        new_groups.append({
            "group_name": group["group_name"],
            "values": new_vals
        })

    return new_groups
