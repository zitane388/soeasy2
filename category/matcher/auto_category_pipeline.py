from category.matcher.category_matcher import (
    match_category_from_json,
    resolve_category_with_llm,
    get_smartstore_category_code,
)
from utils.path import p
import json, os, sys, re


def _clean_image_urls(urls: list[str]) -> list[str]:
    """
    Vision / LLM 입력 전 이미지 URL 정리
    - 문장 끝 마침표, 공백, 개행 제거
    """
    cleaned = []
    for u in urls:
        if not u:
            continue
        u = u.strip()
        # 끝에 붙은 . , 공백 제거
        u = re.sub(r"[.\s]+$", "", u)
        cleaned.append(u)
    return cleaned


def auto_match_category(
    *,
    product_name: str,
    option_names: list[str],
    detail_text: str,
    image_urls: list[str] | None = None,
):
    print("========== [AUTO_MATCH_CATEGORY START] ==========")
    sys.stdout.flush()

    # -------------------------------------------------
    # 1) 카테고리 JSON 로드
    # -------------------------------------------------
    json_path = p("category", "sources", "windly", "windly_categories.json")
    if not os.path.exists(json_path):
        print("[ERROR] category json not found:", json_path)
        print("========== [AUTO_MATCH_CATEGORY END] ==========")
        sys.stdout.flush()
        return None

    with open(json_path, "r", encoding="utf-8") as f:
        category_data = json.load(f)

    print(f"[AUTO_MATCH] category_count={len(category_data)}")
    sys.stdout.flush()

    # -------------------------------------------------
    # 2) 1차 룰/점수 기반 매칭
    # -------------------------------------------------
    result = match_category_from_json(
        category_data=category_data,
        product_name=product_name,
        option_names=option_names,
        detail_text=detail_text,
    )

    if not result or not result.get("candidates"):
        print("[RESULT] no candidates")
        print("========== [AUTO_MATCH_CATEGORY END] ==========")
        sys.stdout.flush()
        return None

    candidates = result["candidates"]
    print(f"[AUTO_MATCH] candidates_count={len(candidates)}")
    sys.stdout.flush()

    # -------------------------------------------------
    # 3) 후보 1개 → 즉시 확정
    # -------------------------------------------------
    if len(candidates) == 1:
        picked = candidates[0]
        print("[AUTO_MATCH] single candidate → auto pick")
        sys.stdout.flush()

    # -------------------------------------------------
    # 4) 후보 여러 개 → LLM 분기
    # -------------------------------------------------
    else:
        print("[AUTO_MATCH] multiple candidates → resolving with LLM")
        sys.stdout.flush()

        cleaned_images = _clean_image_urls(image_urls or [])
        print(f"[AUTO_MATCH] image_urls_for_llm={len(cleaned_images)}")
        if cleaned_images:
            print(f"[AUTO_MATCH] image_url_sample={cleaned_images[0]}")
        sys.stdout.flush()

        refined = resolve_category_with_llm(
            product_name=product_name,
            option_names=option_names,
            detail_text=detail_text,
            match_result=result,
            image_urls=cleaned_images,
        )

        print("[AUTO_MATCH] LLM resolve finished")
        sys.stdout.flush()

        picked = refined.get("final") if refined else None

    # -------------------------------------------------
    # 5) 최종 검증
    # -------------------------------------------------
    if not picked:
        print("[RESULT] final pick failed")
        print("========== [AUTO_MATCH_CATEGORY END] ==========")
        sys.stdout.flush()
        return None

    # -------------------------------------------------
    # 6) 스마트스토어 카테고리
    # -------------------------------------------------
    categories = picked.get("categories", {})
    smartstore_path = categories.get("스마트스토어 카테고리")

    if not smartstore_path:
        print("[ERROR] 스마트스토어 카테고리 없음")
        print("========== [AUTO_MATCH_CATEGORY END] ==========")
        sys.stdout.flush()
        return None

    category_code = get_smartstore_category_code(smartstore_path)

    result_payload = {
        "template_key": picked.get("template_key"),
        "category_name": smartstore_path,
        "category_code": category_code,
    }

    print("[FINAL PAYLOAD]", result_payload)
    print("========== [AUTO_MATCH_CATEGORY END] ==========")
    sys.stdout.flush()

    return result_payload
