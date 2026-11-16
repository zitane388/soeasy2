# utils/option_mode.py

def determine_option_mode(option_groups):
    """
    옵션 그룹 수에 따라 SIMPLE / COMBINATION / NONE 결정
    """
    if not option_groups:
        return "NONE"

    if len(option_groups) == 1:
        return "SIMPLE"

    return "COMBINATION"


def build_simple_options(group):
    """
    단일 옵션 그룹을 네이버 SIMPLE 옵션 형식으로 변환
    예: 색상만 있음 / 사이즈만 있음 / 기타 1개 옵션만 있음
    """
    options = []

    for v in group["values"]:
        opt = {
            "optionName": v["name"],
            "stockQuantity": 30 if not v.get("disabled") else 0
        }

        if "price" in v:
            opt["price"] = v["price"]

        options.append(opt)

    return options


def build_combination_options(option_groups):
    """
    2개 이상 옵션 그룹 → 네이버 조합형 옵션 리스트 생성
    예: 색상 × 사이즈, 길이 × 색상 × 두께 등
    """

    # 모든 그룹의 값 리스트
    value_lists = [g["values"] for g in option_groups]

    # itertools.product 로 모든 조합 생성
    from itertools import product
    option_list = []

    for combo in product(*value_lists):
        # 옵션명 생성
        option_name = " / ".join([v["name"] for v in combo])

        # disabled 있으면 재고 0
        disabled = any(v.get("disabled") for v in combo)

        opt = {
            "optionName": option_name,
            "stockQuantity": 30 if not disabled else 0
        }

        # 가격 누적 (있을 수도 있고 없을 수도 있음)
        price_list = [v.get("price") for v in combo if v.get("price") is not None]
        if price_list:
            opt["price"] = price_list[0]  # 단일 기준 가격만 사용

        option_list.append(opt)

    return option_list
