# utils/option_normalizer.py

from itertools import product


# --------------------------------------------------------
# 1) Uniqlo 전용 옵션 구조 → 표준 구조로 변환
# --------------------------------------------------------
def build_option_groups_from_uniqlo(parsed):
    option_groups = []

    colors = parsed.get("colors")
    if colors:
        option_groups.append({
            "group_name": "색상",
            "values": [
                {
                    "name": c["name"],
                    "code": c.get("code"),
                    "image": c.get("image"),
                    "disabled": False
                }
                for c in colors
            ]
        })

    sizes = parsed.get("sizes")
    if sizes:
        option_groups.append({
            "group_name": "사이즈",
            "values": [
                {
                    "name": s["name"],
                    "code": s.get("code"),
                    "disabled": s.get("disabled", False)
                }
                for s in sizes
            ]
        })

    return option_groups


# --------------------------------------------------------
# 2) 범용 옵션 표준화 (colors/sizes → options)
# --------------------------------------------------------
def normalize_options(parsed):
    if "options" in parsed:
        return parsed   # 이미 표준 구조면 그대로 반환

    colors = parsed.get("colors")
    sizes = parsed.get("sizes")

    option_groups = []

    if colors:
        option_groups.append({
            "group_name": "색상",
            "values": [
                {
                    "name": c["name"],
                    "code": c.get("code"),
                    "image": c.get("image"),
                    "disabled": False
                }
                for c in colors
            ]
        })

    if sizes:
        option_groups.append({
            "group_name": "사이즈",
            "values": [
                {
                    "name": s["name"],
                    "code": s.get("code"),
                    "disabled": s.get("disabled", False)
                }
                for s in sizes
            ]
        })

    parsed["options"] = option_groups
    return parsed


# --------------------------------------------------------
# 3) 옵션 구조 검증기
# --------------------------------------------------------
def ensure_option_schema(parsed):
    """
    options 구조가 표준 형태인지 검증.
    builder에서 오류가 발생하지 않도록 사전 차단.
    """
    opts = parsed.get("options", [])

    if not isinstance(opts, list):
        raise ValueError("parsed['options'] must be a list")

    for group in opts:
        if "group_name" not in group:
            raise ValueError("Each option group must have 'group_name'")
        if "values" not in group:
            raise ValueError("Each option group must have 'values'")
        if not isinstance(group["values"], list):
            raise ValueError("option group 'values' must be a list")

        for val in group["values"]:
            if "name" not in val:
                raise ValueError("option value must have 'name'")
