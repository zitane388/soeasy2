from .base_builder import BaseBuilder


class PurchaseAgentBaseBuilder(BaseBuilder):
    """
    구매대행 상품 템플릿
    BaseBuilder의 originProduct 구조를 그대로 쓰되,
    일부 필드를 구매대행용으로 강제 오버라이드
    """

    def build_purchase_agent_body(self, item, representative, additional):
        brand = item.brand or "Unknown"

        body = super().build(item, [representative] + additional)

        # 구매대행 고정 오버라이드
        origin = body["originProduct"]

        origin["detailAttribute"]["afterServiceInfo"]["afterServiceGuideContent"] = \
            "구매대행 상품은 AS가 불가합니다."

        origin["productInfoProvidedNotice"]["productInfoProvidedNoticeType"] = "ETC"

        origin["detailAttribute"]["productInfoProvidedNotice"]["etc"]["modelName"] = f"{brand}-IMPORT"
        origin["detailAttribute"]["productInfoProvidedNotice"]["etc"]["manufacturer"] = brand
        origin["detailAttribute"]["productInfoProvidedNotice"]["etc"]["afterServiceDirector"] = "구매대행상품"

        # 네이버쇼핑 비등록 강제
        body["smartstoreChannelProduct"]["naverShoppingRegistration"] = False

        return body
