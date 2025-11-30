# naver_uploader/builders/gu/gu_jp_builder.py

from ..purchase_agent_base import PurchaseAgentBaseBuilder
from itertools import product


class GuJpBuilder(PurchaseAgentBaseBuilder):

    def matches(self, brand, country):
        return brand.lower() == "gu" and country == "jp"

    # ======================================================
    # 메인 build()
    # ======================================================
    def build(self, item, detail_images, representative_uploaded_url=None):

        # 1) 구매대행 우선
        if getattr(item, "purchase_agent", False):
            rep = representative_uploaded_url
            add = detail_images
            return self.build_purchase_agent_body(item, rep, add)

        # BaseBuilder build 호출
        body = super().build(
            item,
            detail_images=detail_images,
            representative_uploaded_url=representative_uploaded_url
        )

        parsed = item.parsed_raw
        option_groups = parsed.get("options", [])
        prices = parsed.get("prices", {})

        if not option_groups:
            return body

        if len(option_groups) == 1:
            return self._build_simple(body, option_groups[0])
        else:
            return self._build_combination(body, option_groups, prices, parsed)

    # ======================================================
    # SIMPLE 옵션
    # ======================================================
    def _build_simple(self, body, group):
        group_name = group["group_name"]
        values = group["values"]

        simple_list = []
        for i, v in enumerate(values, start=1):
            simple_list.append({
                "id": i,
                "groupName": group_name,
                "name": v["name"],
                "usable": not v.get("disabled", False)
            })

        body["originProduct"]["detailAttribute"]["optionInfo"] = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": simple_list,
            "optionCustom": [],
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": {},
            "optionCombinations": []
        }

        return body

    # ======================================================
    # COMBINATION 옵션
    # ======================================================
    def _build_combination(self, body, option_groups, prices, parsed):

        group_names = [g["group_name"] for g in option_groups]
        group_values = [g["values"] for g in option_groups]

        raw_base = parsed.get("price", 0)
        if isinstance(raw_base, str):
            try:
                base_price = int(raw_base.replace("¥", "").replace(",", ""))
            except:
                base_price = 0
        else:
            base_price = raw_base

        combinations = list(product(*group_values))
        opt_combs = []
        comb_id = 1

        for combo in combinations:
            names = [v["name"] for v in combo]

            price_val = None
            for v in combo:
                code = v.get("code")
                if code and code in prices:
                    try:
                        price_val = int(prices[code].replace("¥", "").replace(",", ""))
                    except:
                        pass

            if price_val is not None and base_price:
                additional = max(price_val - base_price, 0)
            else:
                additional = 0

            disabled = any(v.get("disabled", False) for v in combo)

            opt_combs.append({
                "optionName1": names[0] if len(names) >= 1 else "",
                "optionName2": names[1] if len(names) >= 2 else "",
                "optionName3": names[2] if len(names) >= 3 else "",
                "optionName4": names[3] if len(names) >= 4 else "",
                "stockQuantity": 0 if disabled else 30,
                "price": additional,
                "usable": not disabled,
                "sellerManagerCode": "",
                "skuYn": False
            })

            comb_id += 1

        comb_group_names = {
            f"optionGroupName{i+1}": group_names[i]
            for i in range(len(group_names))
        }

        body["originProduct"]["detailAttribute"]["optionInfo"] = {
            "simpleOptionSortType": "CREATE",
            "optionSimple": [],
            "optionCustom": [],
            "optionCombinationSortType": "CREATE",
            "optionCombinationGroupNames": comb_group_names,
            "optionCombinations": opt_combs
        }

        return body
