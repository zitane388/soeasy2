# naver_uploader/builders/naver_product_builder.py

from itertools import product
from .base_builder import BaseBuilder
from naver_uploader.utils.price import parse_price


class NaverProductBuilder(BaseBuilder):
    """
    브랜드 / 국가 무관
    ProductItem → 네이버 상품 payload
    """

    def build(self, item, detail_images, representative_uploaded_url=None):

        body = super().build(
            item,
            detail_images=detail_images,
            representative_uploaded_url=representative_uploaded_url,
        )

        # ----------------------------------------
        # 상품 속성(productAttributes) 추가
        # ----------------------------------------
        self._apply_product_attributes(body, item)

        parsed = item.parsed_raw or {}
        option_groups = parsed.get("options", [])
        prices = parsed.get("prices", {})

        option_groups = [
            g for g in option_groups
            if g.get("values")
        ]
        if not option_groups:
            return body

        if len(option_groups) == 1:
            return self._build_simple(body, option_groups[0])

        return self._build_combination(item, body, option_groups, prices)

    # ---------------------------
    # 단일 옵션
    # ---------------------------
    def _build_simple(self, body, group):
        values = group.get("values", [])

        body["originProduct"]["detailAttribute"]["optionInfo"] = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": [
                {
                    "id": i + 1,
                    "groupName": group.get("group_name", ""),
                    "name": v.get("name", ""),
                    "usable": not v.get("disabled", False),
                }
                for i, v in enumerate(values)
            ],
            "optionCustom": [],
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {},
            "optionCombinations": [],
        }
        return body

    # ---------------------------
    # 조합 옵션 (범용 처리)
    # ---------------------------
    def _build_combination(self, item, body, option_groups, prices):

        base_price = item.base_price_krw
        limit = int(base_price * 0.5)  # 네이버 옵션 허용 범위 (±50%)

        group_names = [g.get("group_name", "") for g in option_groups]
        group_values = [g.get("values", []) for g in option_groups]

        combinations = list(product(*group_values))
        option_combinations = []

        for idx, combo in enumerate(combinations):
            names = [v.get("name", "") for v in combo]

            price_val = None
            for v in combo:
                code = v.get("code")
                if code and code in prices:
                    price_val = parse_price(prices[code])
                    break

            disabled = any(v.get("disabled", False) for v in combo)

            # -----------------------------
            # 옵션가 계산 (범용 규칙)
            # -----------------------------
            if price_val is None:
                additional_price = 0
            else:
                diff = price_val - base_price
                if -limit <= diff <= limit:
                    additional_price = diff
                else:
                    additional_price = 0  # 네이버 옵션으로 표현 불가

            # 네이버 필수 조건: 최소 1개 옵션 usable
            if idx == 0:
                additional_price = 0
                stock_qty = max(1, 30)
                usable = True
            else:
                stock_qty = 0 if disabled else 30
                usable = not disabled

            option_combinations.append({
                "optionName1": names[0] if len(names) > 0 else "",
                "optionName2": names[1] if len(names) > 1 else "",
                "optionName3": names[2] if len(names) > 2 else "",
                "optionName4": names[3] if len(names) > 3 else "",
                "stockQuantity": stock_qty,
                "price": int(additional_price),
                "usable": usable,
                "sellerManagerCode": "",
                "skuYn": False,
            })

        body["originProduct"]["detailAttribute"]["optionInfo"] = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": [],
            "optionCustom": [],
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {
                f"optionGroupName{i + 1}": name
                for i, name in enumerate(group_names)
            },
            "optionCombinations": option_combinations,
        }

        return body

    # ---------------------------
    # 상품 속성
    # ---------------------------
    def _apply_product_attributes(self, body, item):
        """
        item.attribute_payload → naver productAttributes 변환
        """

        payload = getattr(item, "attribute_payload", None)
        if not payload:
            return

        product_attrs = []

        for entry in payload:
            attr_id = entry.get("categoryAttributeId")
            if not attr_id:
                continue

            # SELECT / MULTI_SELECT
            if "attributeValueSeqs" in entry:
                for seq in entry.get("attributeValueSeqs", []):
                    product_attrs.append({
                        "attributeSeq": attr_id,
                        "attributeValueSeq": seq
                    })

            # TEXT
            elif "attributeValueText" in entry:
                text = entry.get("attributeValueText")
                if text:
                    product_attrs.append({
                        "attributeSeq": attr_id,
                        "attributeRealValue": text
                    })

        if product_attrs:
            body["originProduct"]["detailAttribute"]["productAttributes"] = product_attrs
