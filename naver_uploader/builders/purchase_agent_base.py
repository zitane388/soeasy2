# naver_uploader/builders/purchase_agent_base.py
import html
from .base_builder import BaseBuilder


class PurchaseAgentBaseBuilder(BaseBuilder):
    """
    구매대행 상품의 공통 JSON 구조를 정의한 Builder.
    어떤 브랜드/국가이든 구매대행이면 이 템플릿을 기반으로 구성된다.
    """

    def build_purchase_agent_body(self, item, representative, additional):
        # 가격 확보
        price = item.parsed_raw.get("price", 10000)
        if isinstance(price, str):
            try:
                price = int(price.replace(",", "").replace("¥", "").strip())
            except:
                price = 10000

        # HTML 상세설명
        detail_html = item.final_description or ""
        detail_html = html.escape(detail_html).replace("\n", "<br>")

        name = item.final_name
        brand = item.brand

        return {
            "originProduct": {
                "statusType": "SALE",
                "leafCategoryId": item.parsed_raw.get("categoryId", "50000826"),

                "name": name,
                "detailContent": detail_html,

                "images": {
                    "representativeImage": {"url": representative},
                    "additionalImages": [{"url": u} for u in additional]
                },

                "salePrice": price,
                "stockQuantity": 10,

                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryAttributeType": "NORMAL",
                    "deliveryCompany": "CJGLS",
                    "deliveryFee": {"deliveryFeeType": "FREE"},

                    "claimDeliveryInfo": {
                        "returnDeliveryCompanyPriorityType": "PRIMARY",
                        "returnDeliveryFee": 0,
                        "exchangeDeliveryFee": 0,
                        "shippingAddressId": getattr(item, "shipping_addr_id", 0),
                        "returnAddressId": getattr(item, "return_addr_id", 0),
                        "freeReturnInsuranceYn": False
                    }
                },

                "detailAttribute": {
                    "minorPurchasable": False,

                    "afterServiceInfo": {
                        "afterServiceTelephoneNumber": "02-0000-0000",
                        "afterServiceGuideContent": "구매대행 상품은 AS가 불가합니다."
                    },

                    "originAreaInfo": {
                        "originAreaType": "INCLUDE_IN_DETAILS",
                        "content": "상세설명 참조",
                        "originAreaCode": "03",
                        "wholeOriginAreaName": "상세설명에 표시",
                        "plural": False
                    },

                    "productInfoProvidedNotice": {
                        "productInfoProvidedNoticeType": "ETC",
                        "etc": {
                            "itemName": "의류",
                            "modelName": f"{brand.upper()}-IMPORT",
                            "manufacturer": brand,
                            "afterServiceDirector": "구매대행상품"
                        }
                    },

                    "naverShoppingSearchInfo": {
                        "manufacturerName": brand,
                        "brandName": brand,
                        "modelName": "IMPORT-0001"
                    }
                }
            },

            "smartstoreChannelProduct": {
                "naverShoppingRegistration": False,
                "channelProductDisplayStatusType": "ON"
            }
        }
