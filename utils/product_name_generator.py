from llm.llm_product_name_generator import (
    generate_product_name_from_llm,
    generate_product_name_from_llm_with_image,
)

import re
import traceback


def normalize_gender_keywords(name: str) -> str:
    print("[DEBUG] normalize_gender_keywords input =", name)

    if not name:
        print("[DEBUG] normalize_gender_keywords → 입력 없음")
        return name

    unisex_patterns = [
        r"남녀공용", r"남녀 공용", r"유니섹스", r"unisex", r"男女兼用",
    ]
    for p in unisex_patterns:
        name = re.sub(p, "", name, flags=re.IGNORECASE)

    male_patterns = [
        r"남자", r"남성용?", r"맨즈?", r"\bmen\b", r"\bmens\b", r"보이즈?", r"소년",
    ]
    for p in male_patterns:
        name = re.sub(p, "남성", name, flags=re.IGNORECASE)

    female_patterns = [
        r"여자", r"여성용?", r"우먼즈?", r"\bwomen\b", r"\bwomens\b", r"걸즈?", r"소녀",
    ]
    for p in female_patterns:
        name = re.sub(p, "여성", name, flags=re.IGNORECASE)

    name = re.sub(r"(남성)\s*\1+", r"\1", name)
    name = re.sub(r"(여성)\s*\1+", r"\1", name)
    name = re.sub(r"\s{2,}", " ", name).strip()

    print("[DEBUG] normalize_gender_keywords output =", name)
    return name


def generate_final_name(
    product_item,
    translated_name: str,
    keyword_list: list[str],
    image_url: str = None
) -> str:

    print("\n================ [NAME GENERATOR START] ================")
    print("translated_name =", translated_name)
    print("keyword_list =", keyword_list)
    print("image_url =", image_url)
    print("product_item.model_number =", getattr(product_item, "model_number", None))

    try:
        if not translated_name or not keyword_list:
            print("[SKIP] translated_name 또는 keyword_list 없음")
            return ""

        # -----------------------------
        # LLM 호출
        # -----------------------------
        print("[DEBUG] LLM 호출 직전")

        if image_url and image_url.startswith("http"):
            print("[DEBUG] Vision LLM 호출")
            result = generate_product_name_from_llm_with_image(
                product_name=translated_name,
                keywords=keyword_list,
                image_url=image_url,
            )
        else:
            print("[DEBUG] Text LLM 호출")
            result = generate_product_name_from_llm(
                product_name=translated_name,
                keywords=keyword_list,
            )

        print("[DEBUG] LLM 결과 =", result, "| type =", type(result))

        if not result:
            print("[ERROR] LLM 결과가 비어있음")
            return ""

        # -----------------------------
        # 성별 정규화
        # -----------------------------
        result = normalize_gender_keywords(result)

        # -----------------------------
        # 모델넘버 추가
        # -----------------------------
        model_no = getattr(product_item, "model_number", None)
        print("[DEBUG] model_no =", model_no)

        if model_no:
            model_no = str(model_no).strip()
            if model_no.lower() not in result.lower():
                result = f"{result} {model_no}"

        print("[DEBUG] 모델번호 추가 후 =", result)

        # -----------------------------
        # 공백 정리
        # -----------------------------
        result = re.sub(r"\s{2,}", " ", result).strip()

        print("[FINAL RESULT RETURN] =", result)
        print("================ [NAME GENERATOR END] ================\n")
        return result

    except Exception as e:
        print("[NAME GENERATOR ERROR]")
        traceback.print_exc()
        print("================ [NAME GENERATOR CRASH] ================\n")
        return ""
