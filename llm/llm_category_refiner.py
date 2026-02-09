# llm/llm_category_refiner.py

from llm.llm_formatter import CATEGORY_PICK_PROMPT
from llm.llm_client import request_llm, request_llm_with_image


def llm_pick_best_category(
    product_name: str,
    option_names: list[str],
    filtered_description: str,
    candidates: list[dict],
    image_urls: list[str] | None = None,
) -> str | None:
    """
    동률 후보 중 LLM이 최종 1개 template_key를 추천
    실패하면 None 반환
    """

    if not candidates or len(candidates) < 2:
        return None

    candidate_keys = []
    for c in candidates:
        key = c.get("template_key")
        if key:
            candidate_keys.append(f"- {key}")

    if len(candidate_keys) < 2:
        return None

    prompt = CATEGORY_PICK_PROMPT.format(
        product_name=product_name,
        option_names=", ".join(option_names[:10]),
        filtered_description=filtered_description or "",
        candidate_list="\n".join(candidate_keys),
    )

    # ----------------------------
    # LLM 호출 (공식 경로)
    # ----------------------------
    if image_urls:
        response = request_llm_with_image(
            prompt=prompt,
            image_url=image_urls[0]
        )
    else:
        response = request_llm(prompt)

    if not response:
        return None

    # ----------------------------
    # 결과 파싱
    # ----------------------------
    for line in response.splitlines():
        if line.startswith("선택:"):
            picked = line.replace("선택:", "").strip()
            for c in candidates:
                if c.get("template_key") == picked:
                    return picked

    return None
