# naver_uploader/builders/base_builder.py

import html


class BaseBuilder:
    """
    스마트스토어 상품 등록 JSON의 기본 구조를 생성하는 공통 Builder.

    - 브랜드/국가별 Builder 클래스는 BaseBuilder 를 상속하여
      필요한 부분만 override 하면 됨.
    """

    def __init__(self):
        pass

    # ---------------------------------------------------------
    # 외부에서 호출하는 메인 함수
    # ---------------------------------------------------------
    def build(self, item, uploaded_images):
        """
        item : ProductItem
        uploaded_images : SmartStore CDN에 업로드된 이미지 URL 리스트
        """

        name = item.final_name
        desc = item.final_description or ""

        # HTML safe 변환 + 줄바꿈 치환
        desc_html = html.escape(desc).replace("\n", "<br>")

        # 가격 확보 (없으면 0)
        price = item.parsed_raw.get("price", 0)
        if isinstance(price, str):
            try:
                price = int(price.replace(",", "").strip())
            except:
                price = 0

        # 기본 JSON 골격
        body = {
            "subject": name,
            "detailContent": desc_html,

            # 대표 이미지 (첫 번째 이미지)
            "representativeImage": uploaded_images[0] if uploaded_images else None,

            # 나머지 부가 이미지
            "additionalImages": uploaded_images[1:] if uploaded_images else [],

            # 판매가
            "salePrice": price,

            # 판매상태
            "statusType": "SALE",

            # 기본 재고
            "stockQuantity": 50,

            # 배송 설정 (기본값)
            "delivery": {
                "method": "DELIVERY",
                "feeType": "PAID",
                "deliveryFee": 3000
            },

            # 옵션은 기본적으로 없음 (브랜드/국가별 Builder에서 override)
            "optionManageType": "NORMAL",
            "options": []
        }

        # 브랜드/국가별 builder가 옵션 변환 구현 가능
        body = self.apply_brand_specific_rules(item, body)

        return body

    # ---------------------------------------------------------
    # 브랜드/국가별 커스텀 로직을 override 하는 함수
    # ---------------------------------------------------------
    def apply_brand_specific_rules(self, item, body: dict) -> dict:
        """
        유니클로 JP / US / 글로벌 등에서
        색상/사이즈/옵션을 스마트스토어 규격으로 변환하는 부분.

        기본 BaseBuilder에서는 아무 작업도 하지 않는다.
        """
        return body
