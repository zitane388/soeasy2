# naver_uploader/builders/purchase_agent_base.py

from .base_builder import BaseBuilder


class PurchaseAgentBaseBuilder(BaseBuilder):
    """
    구매대행 상품 템플릿
    BaseBuilder에서 생성한 기본 구조 위에
    구매대행 고정 규칙을 강제 적용한다.
    """

    def build_purchase_agent_body(self, item, representative, additional):
    
        body = super().build(
            item,
            detail_images=additional,
            representative_uploaded_url=representative,
        )
        origin = body["originProduct"]

        # ------------------------------------------------------
        # ① 구매대행은 옵션을 SIMPLE 형태로 강제(또는 무옵션)
        # ------------------------------------------------------
        origin["optionManageType"] = "SIMPLE"

        # SIMPLE 옵션으로 강제 리셋 (빈 값)
        origin["detailAttribute"]["optionInfo"] = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": [],
            "optionCustom": [],
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {},
            "optionCombinations": []
        }

        # ------------------------------------------------------
        # ② 구매대행 고정 A/S 정보
        # ------------------------------------------------------
        origin["detailAttribute"]["afterServiceInfo"] = {
            "afterServiceTelephoneNumber": "010-3013-5686",
            "afterServiceGuideContent": (
                "톡톡 또는 문자로 문의주시면 빠르게 응답드리겠습니다."
            )
        }

        # ------------------------------------------------------
        # ③ 상품정보제공고시 (구매대행 전용)
        # ------------------------------------------------------
        notice = origin["detailAttribute"]["productInfoProvidedNotice"]["etc"]
        notice["modelName"] = f"{item.brand}-IMPORT"
        notice["manufacturer"] = "수입(병행수입)"
        notice["afterServiceDirector"] = "구매대행상품"

        # ------------------------------------------------------
        # ④ 원산지 표시
        # ------------------------------------------------------
        origin["detailAttribute"]["originAreaInfo"] = {
            "originAreaType": "INCLUDE_IN_DETAILS",
            "content": "상세설명에 표시",
            "originAreaCode": "03",
            "wholeOriginAreaName": "상세설명에 표시",
            "plural": False
        }

        # ------------------------------------------------------
        # ⑤ 네이버쇼핑 미등록 고정
        # ------------------------------------------------------
        body["smartstoreChannelProduct"]["naverShoppingRegistration"] = False

        return body
