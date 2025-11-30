import os
import json
from llm.llm_client import request_llm
import llm.llm_formatter as formatter


class CategoryMatcher:
    """
    최종 구조:
    1) 상품명 기반 → LLM이 중분류 1개 선택
    2) 선택된 중분류의 소분류/세분류 후보 생성
    3) 후보 트리를 LLM에 전달하여 최종 카테고리 선택
    """

    mid_groups = {}
    small_groups = {}
    sub_groups = {}

    @classmethod
    def load_groups(cls):
        print("=======================================")
        print("[CategoryMatcher] JSON 기반 카테고리 그룹 로딩 시작")
        base = "data"

        mid_path = os.path.join(base, "category_groups_mid.json")
        small_path = os.path.join(base, "category_groups_small.json")
        sub_path = os.path.join(base, "category_groups_sub.json")

        if os.path.exists(mid_path):
            with open(mid_path, "r", encoding="utf-8") as f:
                cls.mid_groups = json.load(f)

        if os.path.exists(small_path):
            with open(small_path, "r", encoding="utf-8") as f:
                cls.small_groups = json.load(f)

        if os.path.exists(sub_path):
            with open(sub_path, "r", encoding="utf-8") as f:
                cls.sub_groups = json.load(f)

        print("[CategoryMatcher] JSON 카테고리 그룹 로딩 완료")
        print("=======================================")

    # -------------------------------------------------------
    # LLM의 선택 결과 파싱
    # -------------------------------------------------------
    @staticmethod
    def parse_selected_mid(raw):
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("- 선택:"):
                return line.replace("- 선택:", "").strip()
        return None

    # -------------------------------------------------------
    # 1) 상품명 기반: 중분류 1개 선택
    # -------------------------------------------------------
    @classmethod
    def select_mid(cls, product_name):
        all_mid_list = []
        for mids in cls.mid_groups.values():
            all_mid_list.extend(mids)

        print("\n=======================")
        print("[DEBUG] LLM 전달 MID_LIST:")
        print("=======================")
        for m in all_mid_list:
            print("-", m)
        print("=======================\n")

        prompt = formatter.CATEGORY_MID_SELECT_PROMPT.format(
            PRODUCT_NAME=product_name,
            MID_LIST="\n".join(all_mid_list)
        )

        raw = request_llm(prompt)
        print("[CategoryMatcher] LLM 중분류 선택(raw):", raw)

        selected = cls.parse_selected_mid(raw)
        if not selected:
            print("[CategoryMatcher] 중분류 선택 실패 → fallback 사용")
            selected = cls.fallback_mid(product_name)

        print("[CategoryMatcher] 최종 선택된 중분류:", selected)
        return selected

    # 간단한 fallback: 상품명과 가장 많이 매칭되는 중분류 선택
    @classmethod
    def fallback_mid(cls, product_name):
        product_name_l = product_name.lower()
        best_mid = None
        best_score = 0

        for mids in cls.mid_groups.values():
            for mid in mids:
                score = sum(1 for w in mid.lower().split() if w in product_name_l)
                if score > best_score:
                    best_score = score
                    best_mid = mid

        return best_mid or list(cls.mid_groups.values())[0][0]

    # -------------------------------------------------------
    # 2) 선택된 중분류의 모든 후보 구성
    # -------------------------------------------------------
    @classmethod
    def build_candidate_list(cls, mid):
        candidates = []
        smalls = cls.small_groups.get(mid, [])

        for small_entry in smalls:
            small_name = small_entry["name"]
            small_code = small_entry.get("code")

            if small_code:
                candidates.append(f"{small_code} | {mid} > {small_name}")
            else:
                subs = cls.sub_groups.get(small_name, [])
                for s in subs:
                    code = s["code"]
                    name = s["name"]
                    candidates.append(f"{code} | {mid} > {small_name} > {name}")

        print("[CategoryMatcher] 하위 후보 개수:", len(candidates))
        return candidates

    # -------------------------------------------------------
    # 3) LLM 최종 카테고리 선택
    # -------------------------------------------------------
    @classmethod
    def parse_final_selected(cls, raw):
        for line in raw.splitlines():
            if line.startswith("- 최종선택:"):
                return line.replace("- 최종선택:", "").strip()
        return None

    @classmethod
    def select_final_category(cls, product_name, category_tree):
        import json
        prompt = formatter.CATEGORY_FINAL_SELECT_PROMPT.format(
            PRODUCT_NAME=product_name,
            CATEGORY_TREE_JSON=json.dumps(category_tree, ensure_ascii=False, indent=2)
        )

        raw = request_llm(prompt)
        print("[CategoryMatcher] LLM 최종 선택(raw):", raw)

        return cls.parse_final_selected(raw)

    # -------------------------------------------------------
    # 전체 실행
    # -------------------------------------------------------
    @classmethod
    def match(cls, product_name: str):
        if not cls.mid_groups:
            cls.load_groups()

        print("[CategoryMatcher] 매칭 시작 →", product_name)
        print("===========================================")

        mid = cls.select_mid(product_name)
        candidates = cls.build_candidate_list(mid)
        final = cls.select_final_category(product_name, candidates)

        print("\n[CategoryMatcher] 🏆 최종 카테고리 선택 결과:")
        print("  ", final)
        print("===========================================")

        return final
