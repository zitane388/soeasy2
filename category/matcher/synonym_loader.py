# category/matcher/synonym_loader.py
import json
import os

_SYNONYM_INDEX = None


def load_synonym_index():
    global _SYNONYM_INDEX
    if _SYNONYM_INDEX is not None:
        return _SYNONYM_INDEX

    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "sources")
    )
    path = os.path.join(base_dir, "synonym_group.json")

    with open(path, "r", encoding="utf-8") as f:
        groups = json.load(f)

    index = {}
    for group in groups:
        for kw in group:
            index[kw] = group

    _SYNONYM_INDEX = index
    return index

def expand_keywords_with_synonyms(keywords: list[str]) -> list[str]:
    synonym_index = load_synonym_index()

    expanded = set(keywords)

    for kw in keywords:
        group = synonym_index.get(kw)
        if group:
            expanded.update(group)

    return list(expanded)

def get_synonym_group_weight(keywords, global_weight_map, synonym_index):
    """
    keywords 중 동의어 그룹이 있는 경우
    해당 그룹 내 키워드들의 weight 최댓값 반환
    """
    max_weight = 0.0

    for kw in keywords:
        group = synonym_index.get(kw)
        if not group:
            continue

        for gkw in group:
            w = global_weight_map.get(gkw, 1.0)
            if w > max_weight:
                max_weight = w

    return max_weight if max_weight > 0 else None

def get_group_max_weights(keywords, global_weight_map, synonym_index):
    """
    동의어 그룹별 최고 weight 반환
    return: { keyword: group_max_weight }
    """
    group_max = {}

    for kw in keywords:
        group = synonym_index.get(kw)
        if not group:
            continue

        max_w = max(
            global_weight_map.get(gkw, 1.0)
            for gkw in group
        )

        for gkw in group:
            group_max[gkw] = max_w

    return group_max

