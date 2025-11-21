# naver_uploader/builders/uniqlo/jp_builder.py

from ..purchase_agent_base import PurchaseAgentBaseBuilder


class UniqloJpBuilder(PurchaseAgentBaseBuilder):
    """
    유니클로 JP Builder (옵션 처리 + 구매대행 처리 통합)
    """

    def matches(self, brand, country):
        return brand == "uniqlo" and country == "jp"

    def apply_brand_specific_rules(self, item, body):
        """
        구매대행 모드 우선 처리
        """
        if getattr(item, "purchase_agent", False):
            rep = body.get("representativeImage")
            add = body.get("additionalImages", [])
            return self.build_purchase_agent_body(item, rep, add)

        # -----------------------------
        # 일반 상품 모드 (기존 옵션 처리)
        # -----------------------------
        parsed = item.parsed_raw

        if "colors" not in parsed or "sizes" not in parsed:
            body["optionManageType"] = "NORMAL"
            body["options"] = []
            return body

        colors = parsed.get("colors", [])
        sizes = parsed.get("sizes", [])
        prices = parsed.get("prices", {})

        option_list = []

        for c in colors:
            c_name = c.get("name")
            c_code = c.get("code")
            c_price = prices.get(c_code)

            if isinstance(c_price, str):
                try:
                    c_price = int(c_price.replace("¥", "").replace(",", "").strip())
                except:
                    c_price = None

            for s in sizes:
                s_name = s.get("name")
                disabled = s.get("disabled", False)

                opt = {
                    "optionName": f"{c_name} / {s_name}",
                    "stockQuantity": 30 if not disabled else 0
                }

                if c_price is not None:
                    opt["price"] = c_price

                option_list.append(opt)

        body["optionManageType"] = "COMBINATION"
        body["options"] = option_list

        body["optionCombination"] = [
            {"optionName": "색상", "optionValue": [c["name"] for c in colors]},
            {"optionName": "사이즈", "optionValue": [s["name"] for s in sizes]},
        ]

        return body
