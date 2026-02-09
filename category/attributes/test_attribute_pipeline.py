import sys
import os

# 프로젝트 루트 (soeasy2) 경로 강제 추가
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from category.attributes.attribute_pipeline import auto_match_attributes
from category.attributes.smartstore_login import login_and_create_session
from llm.llm_attribute_resolver import resolve_attributes_with_llm


def main():
    # ----------------------------------
    # SmartStore 로그인 (실제 로그인)
    # ----------------------------------
    session = login_and_create_session(
        naver_id="junhwi5686@gmail.com",   # ← 문자열로 직접 전달
        naver_pw="tkfkek3013",          # ← 문자열로 직접 전달
        headless=False,               # 테스트 시 False 권장
    )

    # ----------------------------------
    # 테스트 입력 데이터
    # ----------------------------------
    category_code = "50000830"  # 패션의류 > 남성의류 > 티셔츠

    product_name = "유니클로 여성 에어리즘 코튼 스트라이프 티셔츠"

    option_names = [
        "오프화이트",
        "블랙",
        "XS", "S", "M", "L", "XL", "XXL", "3XL",
    ]

    detail_text = """
상품설명
편안한 착용감을 제공하는 에어리즘 소재의 티셔츠입니다.
정전기 방지 기능이 있어 땀이 쉽게 마르며 부드러운 질감을 가지고 있습니다.
약간 좁은 네크라인과 리브 디자인으로 세련된 느낌을 줍니다.
리ラック스 핏과 기본 길이로 단독으로도 멋스럽게 착용 가능합니다.
옆트임과 앞뒤 길이 차이가 있어 포인트를 더했습니다.

사이즈 안내
XS, XXL, 3XL 사이즈는 온라인 스토어에서만 구매 가능합니다.

소재
겉감: 면 70%, 복합섬유(폴리에스터) 30%
"""

    image_urls = []  # 테스트에서는 이미지 생략

    # ----------------------------------
    # 속성 자동 매칭 실행
    # ----------------------------------
    print("\n==============================")
    print("[TEST] AUTO ATTRIBUTE MATCH")
    print("==============================")

    result = auto_match_attributes(
        category_code=category_code,
        product_name=product_name,
        option_names=option_names,
        detail_text=detail_text,
        image_urls=image_urls,
        llm_resolver=resolve_attributes_with_llm,  # 1차 테스트는 LLM 없이
        session=session,
    )

    # ----------------------------------
    # 결과 출력
    # ----------------------------------
    print("\n========== [MATCHED ATTRIBUTES] ==========")
    for m in result["matched"]:
        print(
            f"- {m['attributeName']} "
            f"({m['classificationType']}) "
            f"=> values={m.get('pickedValueSeqs')} text={m.get('pickedText')}"
        )

    print("\n========== [SMARTSTORE PAYLOAD] ==========")
    for p in result["payload"]:
        print(p)

    print("\n========== [MISSING REQUIRED ATTRIBUTES] ==========")
    for miss in result["unmatched_required"]:
        print(
            f"- {miss.get('attributeName')} "
            f"({miss.get('attributeClassificationType')})"
        )


if __name__ == "__main__":
    main()
