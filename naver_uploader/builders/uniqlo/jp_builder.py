from ..purchase_agent_base import PurchaseAgentBaseBuilder


class UniqloJpBuilder(PurchaseAgentBaseBuilder):
    """
    유니클로 JP Builder
    - 구매대행 여부 판단 후 BaseBuilder 또는 PurchaseAgent 템플릿으로 처리
    """

    def matches(self, brand, country):
        return brand == "uniqlo" and country == "jp"

    def build(self, item, uploaded_images):
        # 구매대행이면 무조건 구매대행 템플릿 사용
        if getattr(item, "purchase_agent", False):
            rep = uploaded_images[0]
            add = uploaded_images[1:]
            return self.build_purchase_agent_body(item, rep, add)

        # 기본 템플릿
        body = super().build(item, uploaded_images)
        parsed = item.parsed_raw

        # 옵션 없으면 NORMAL
        if "colors" not in parsed or "sizes" not in parsed:
            return body

        colors = parsed["colors"]
        sizes = parsed["sizes"]
        prices = parsed.get("prices", {})

        option_list = []

        for c in colors:
            c_name = c["name"]
            c_code = c.get("code")
            base_price = prices.get(c_code)

            if isinstance(base_price, str):
                try:
                    base_price = int(base_price.replace("¥", "").replace(",", ""))
                except:
                    base_price = None

            for s in sizes:
                s_name = s["name"]
                disabled = s.get("disabled", False)

                opt = {
                    "optionName": f"{c_name} / {s_name}",
                    "stockQuantity": 30 if not disabled else 0
                }

                if base_price is not None:
                    opt["price"] = base_price

                option_list.append(opt)

        body["originProduct"]["optionManageType"] = "COMBINATION"
        body["originProduct"]["options"] = option_list

        body["originProduct"]["optionCombination"] = [
            {"optionName": "색상", "optionValue": [c["name"] for c in colors]},
            {"optionName": "사이즈", "optionValue": [s["name"] for s in sizes]},
        ]

        return body
