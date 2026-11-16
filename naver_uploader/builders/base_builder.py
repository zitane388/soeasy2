# naver_uploader/builders/base_builder.py

import html

SHIPPING_ADDR_ID = 106712350
RETURN_ADDR_ID   = 106682366


class BaseBuilder:

    def build(self, item, detail_images, representative_uploaded_url=None):

        # -------------------------------
        # 기본 필드
        # -------------------------------
        name = item.final_name or "상품명 미지정"
        desc = item.final_detail_text or ""

        price = item.base_price_krw

        category = item.category_code
        brand    = item.brand or ""

        # -------------------------------
        # 이미지 구성
        # -------------------------------
        representative = (
            {"url": representative_uploaded_url}
            if representative_uploaded_url
            else {"url": None}
        )

        optional = []
        for u in detail_images:
            if isinstance(u, str):
                optional.append({"url": u})
            else:
                optional.append(u)

        if len(optional) > 9:
            optional = optional[:9]

        shipping_id = getattr(item, "shipping_addr_id", SHIPPING_ADDR_ID)
        return_id   = getattr(item, "return_addr_id", RETURN_ADDR_ID)

        # -------------------------------
        # 옵션 기본 틀
        # -------------------------------
        option_info_empty = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": [],
            "optionCustom": [],
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {},
            "optionCombinations": []
        }

        # ----------------------------------------------------
        # 🔥 naverShoppingSearchInfo (detailAttribute 내부에 위치해야 함)
        # ----------------------------------------------------
        naver_shopping_info = {
            "modelName": item.model_number or "",
            "manufacturerName": brand,
            "brandName": brand
        }

        # -------------------------------
        # 최종 SmartStore body
        # -------------------------------
        body = {
            "originProduct": {
                "statusType": "SALE",
                "leafCategoryId": category,

                "name": name,
                "detailContent": desc,

                "images": {
                    "representativeImage": representative,
                    "optionalImages": optional
                },

                "salePrice": price,
                "stockQuantity": 50,

                "deliveryInfo": {
                    "deliveryType": "DELIVERY",
                    "deliveryAttributeType": "NORMAL",
                    "deliveryCompany": "CJGLS",
                    "deliveryFee": {
                        "deliveryFeeType": "FREE",
                        "deliveryFeePayType": "PREPAID",
                        "baseFee": 0,
                        "deliveryFeeByArea": {
                            "deliveryAreaType": "AREA_3",
                            "area2extraFee": 5000,
                            "area3extraFee": 5000
                        }
                    },
                    "claimDeliveryInfo": {
                        "returnDeliveryCompanyPriorityType": "PRIMARY",
                        "returnDeliveryFee": 40000,
                        "exchangeDeliveryFee": 80000,
                        "shippingAddressId": shipping_id,
                        "returnAddressId": return_id,
                        "freeReturnInsuranceYn": False
                    }
                },

                "detailAttribute": {
                    "minorPurchasable": True,

                    "optionInfo": option_info_empty,

                    "afterServiceInfo": {
                        "afterServiceTelephoneNumber": "010-3013-5686",
                        "afterServiceGuideContent": "톡톡이나 문자로 문의주시면 최대한 빠르게 답변 드리겠습니다."
                    },

                    "originAreaInfo": {
                        "originAreaType": "INCLUDE_IN_DETAILS",
                        "content": "상세설명에 표시",
                        "originAreaCode": "03",
                        "wholeOriginAreaName": "상세설명에 표시",
                        "plural": False
                    },
                    
                    "certificationTargetExcludeContent": {
                        "kcCertifiedProductExclusionYn": "KC_EXEMPTION_OBJECT",
                        "greenCertifiedProductExclusionYn": True,
                        "kcExemptionType": "OVERSEAS"
                    },

                    "productInfoProvidedNotice": {
                        "productInfoProvidedNoticeType": "ETC",
                        "etc": {
                            "itemName": "상품상세 참조",
                            "modelName": "상품상세 참조",
                            "manufacturer": "상품상세 참조",
                            "customerServicePhoneNumber": "010-3013-5686"
                        }
                    },

                    "naverShoppingSearchInfo": naver_shopping_info
                }
            },

            "smartstoreChannelProduct": {
                "naverShoppingRegistration": False,
                "channelProductDisplayStatusType": "SUSPENSION"
            }
        }

        return body
