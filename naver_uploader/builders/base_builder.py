# naver_uploader/builders/base_builder.py

import html

# 주소 ID (네이버 필수값)
SHIPPING_ADDR_ID = 106712350
RETURN_ADDR_ID   = 106712349

class BaseBuilder:

    def build(self, item, uploaded_images):

        # 기본 필드들
        name = item.final_name or "상품명 미지정"
        desc = item.final_description or ""
        desc_html = html.escape(desc).replace("\n", "<br>")

        raw_price = item.parsed_raw.get("price", 10000)
        if isinstance(raw_price, str):
            try:
                raw_price = int(raw_price.replace(",", "").replace("¥", "").strip())
            except:
                raw_price = 10000

        # 네이버 규칙: 최소 10원
        price = max(raw_price, 10)

        category = item.parsed_raw.get("categoryId", "50000826")
        brand = item.brand or "Unknown"

        representative = uploaded_images[0] if uploaded_images else None
        additional = uploaded_images[1:] if uploaded_images else []

        # 주소 ID (네이버 필수)
        shipping_id = getattr(item, "shipping_addr_id", SHIPPING_ADDR_ID)
        return_id   = getattr(item, "return_addr_id", RETURN_ADDR_ID)

        body = {
            "originProduct": {
                "statusType": "SALE",
                "leafCategoryId": category,

                "name": name,
                "detailContent": desc_html,

                "images": {
                    "representativeImage": {"url": representative},
                    "additionalImages": [{"url": u} for u in additional]
                },

                "salePrice": price,
                "stockQuantity": 50,

                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryAttributeType": "NORMAL",

                    # ★ 네이버 필수 3개 값 수정 완료
                    "deliveryCompany": "CJGLS",
                    "deliveryFee": {
                        "deliveryFeeType": "FREE",
                        "deliveryFeePayType": "PREPAID",
                        "baseFee": 3000
                    },

                    "claimDeliveryInfo": {
                        "returnDeliveryCompanyPriorityType": "PRIMARY",
                        "returnDeliveryFee": 3000,
                        "exchangeDeliveryFee": 3000,
                        "shippingAddressId": shipping_id,
                        "returnAddressId": return_id,
                        "freeReturnInsuranceYn": False
                    }
                },

                "detailAttribute": {
                    "minorPurchasable": False,

                    "afterServiceInfo": {
                        "afterServiceTelephoneNumber": "02-0000-0000",
                        "afterServiceGuideContent": "상세설명 참조"
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
                            "modelName": "DEFAULT-MODEL",
                            "manufacturer": brand,
                            "afterServiceDirector": "판매자"
                        }
                    }
                }
            },

            "smartstoreChannelProduct": {
                "naverShoppingRegistration": False,
                "channelProductDisplayStatusType": "ON"
            }
        }

        return body
