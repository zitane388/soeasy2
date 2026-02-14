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


def _build_option_axes_from_options(options):
    axes = []
    for i, group in enumerate(options):
        axis_key = group.get("group_code") or f"axis_{i + 1}"
        axis_name = group.get("group_name") or axis_key
        values = []

        for j, val in enumerate(group.get("values", [])):
            values.append({
                "value_id": val.get("code") or f"{axis_key}_{j + 1}",
                "name": val.get("name"),
                "code": val.get("code"),
                "disabled": bool(val.get("disabled", False)),
                "image": val.get("image"),
                "chip_image": val.get("chip_image"),
            })

        axes.append({
            "axis_key": axis_key,
            "axis_name": axis_name,
            "values": values,
        })

    return axes


def _pick_variant_price(parsed, selected_values_by_axis):
    prices = parsed.get("prices")
    if isinstance(prices, dict) and prices:
        color_axis = selected_values_by_axis.get("색상")
        if color_axis:
            color_code = color_axis.get("code")
            if color_code in prices:
                return prices[color_code]

            color_name = color_axis.get("name")
            if color_name in prices:
                return prices[color_name]

    return parsed.get("price")


def normalize_option_axes_and_variants(parsed):
    """
    options 기반으로 option_axes + variants를 생성한다.
    기존 colors/sizes/options는 유지하고, 신규 필드를 추가한다.
    """
    parsed = normalize_options(parsed)

    options = parsed.get("options", [])
    if not isinstance(options, list):
        return parsed

    axes = _build_option_axes_from_options(options)
    parsed["option_axes"] = axes

    if not axes:
        parsed["option_variants"] = []
        if "variants" not in parsed or isinstance(parsed.get("variants"), list):
            parsed["variants"] = []
        return parsed

    axis_names = [a["axis_name"] for a in axes]
    axis_keys = [a["axis_key"] for a in axes]
    value_lists = [a["values"] for a in axes]

    variants = []
    for idx, combo in enumerate(product(*value_lists), start=1):
        values_by_axis_name = {axis_names[i]: combo[i] for i in range(len(combo))}
        values_by_axis_key = {axis_keys[i]: combo[i] for i in range(len(combo))}

        option_values = {
            axis_keys[i]: (combo[i].get("name") or "")
            for i in range(len(combo))
        }
        option_codes = {
            axis_keys[i]: combo[i].get("code")
            for i in range(len(combo))
        }
        disabled = any(v.get("disabled", False) for v in combo)

        image = None
        for v in combo:
            image = v.get("image") or image
            if image:
                break

        variants.append({
            "variant_id": f"var_{idx}",
            "option_values": option_values,
            "option_codes": option_codes,
            "disabled": disabled,
            "price": _pick_variant_price(parsed, values_by_axis_name),
            "image": image,
            "raw": values_by_axis_key,
        })

    parsed["option_variants"] = variants

    # Backward-compatible: only map to parsed["variants"] when it's absent or already list.
    if "variants" not in parsed or isinstance(parsed.get("variants"), list):
        parsed["variants"] = variants

    return parsed
