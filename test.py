import os
import re
import math
from bs4 import BeautifulSoup
from collections import Counter
from llm.llm_option_filter import pick_option_groups_by_llm

OPTION_HINT_KEYWORDS = {
    "variant", "swatch", "chip", "option"
}

def class_overlap_score(node1, node2):
    c1 = set(node1.get("class", []) or [])
    c2 = set(node2.get("class", []) or [])
    if not c1 or not c2:
        return 0.0
    inter = len(c1 & c2)
    union = len(c1 | c2)
    return inter / union  # 0.0 ~ 1.0

def value_diversity_score(values):
    total = len(values)
    if total == 0:
        return 0.0
    counts = Counter(values)
    k = len(counts)
    if k <= 1:
        return 0.0
    probs = [c / total for c in counts.values()]
    entropy = -sum(p * math.log(p, 2) for p in probs)
    return entropy / math.log(k, 2)


def is_visible(node):
    """
    해당 노드가 시각적으로 숨겨져 있는지(display: none, hidden 등) 판별합니다.
    """
    # 1. 태그 자체가 hidden 속성을 가졌는지 확인
    if node.has_attr('hidden'):
        return False
    
    # 2. 클래스명에 숨김을 의미하는 키워드가 있는지 확인
    # 'dn' (display: none), 'hidden', 'hide', 'visually-hidden' 등
    HIDDEN_CLASS_KEYWORDS = ['dn', 'hide', 'hidden', 'visually-hidden', 'sr-only']
    classes = node.get('class', [])
    if any(keyword in ' '.join(classes).lower() for keyword in HIDDEN_CLASS_KEYWORDS):
        return False
    
    # 3. 인라인 스타일 검사
    style = node.get('style', '').lower()
    if 'display:none' in style.replace(" ", "") or 'visibility:hidden' in style.replace(" ", ""):
        return False
        
    return True

import re

SEMANTIC_ATTRS = {
    "aria-label",
    "aria-valuetext",
    "aria-labelledby",
    "title",
    "value",
    "name",
    "id",
    "for",
}

BAD_TOKENS = {
    "", "image", "img", "icon", "button", "option",
    "thumbnail", "chip", "select"
}


def _clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    return s


def _is_meaningful(s: str) -> bool:
    if not s:
        return False
    if len(s) > 40:        # 너무 긴 문장 제거
        return False
    if s.lower() in BAD_TOKENS:
        return False
    return True


def _split_attr_value(val: str) -> list[str]:
    """
    BLUE-68-1 → ["BLUE"]
    color_blue → ["blue"]
    """
    val = val.replace("_", " ").replace("-", " ")
    tokens = re.split(r"\s+", val)
    return [t for t in tokens if _is_meaningful(t)]


def extract_option_value_candidates(node):
    candidates = {
        "text": [],
        "alt": [],
        "aria": [],
        "attr": [],
    }

    # -----------------------------------
    # 1️⃣ 가시 텍스트 (최우선)
    # -----------------------------------
    try:
        text = get_visible_text(node)
    except Exception:
        text = ""

    if _is_meaningful(text):
        candidates["text"].append(text)

    # -----------------------------------
    # 2️⃣ img alt (컬러칩 핵심)
    # -----------------------------------
    for img in node.find_all("img"):
        alt = img.get("alt", "")
        alt = _clean_text(alt)
        if _is_meaningful(alt):
            candidates["alt"].append(alt)

    # -----------------------------------
    # 3️⃣ aria 계열
    # -----------------------------------
    for el in [node] + list(node.find_all(True, recursive=True)):
        for attr in ("aria-label", "aria-valuetext"):
            if el.has_attr(attr):
                val = _clean_text(str(el.get(attr)))
                if _is_meaningful(val):
                    candidates["aria"].append(val)

    # aria-labelledby → 실제 텍스트 resolve
    if node.has_attr("aria-labelledby"):
        ref_id = node.get("aria-labelledby")
        ref = node.find(id=ref_id)
        if ref:
            val = _clean_text(ref.get_text(" ", strip=True))
            if _is_meaningful(val):
                candidates["aria"].append(val)

    # -----------------------------------
    # 4️⃣ 의미 있는 속성 (보조)
    # -----------------------------------
    for el in [node] + list(node.find_all(True, recursive=True)):
        for attr in SEMANTIC_ATTRS:
            if el.has_attr(attr):
                raw = str(el.get(attr))
                for tok in _split_attr_value(raw):
                    candidates["attr"].append(tok)

    # -----------------------------------
    # 5️⃣ 중복 제거
    # -----------------------------------
    for k in candidates:
        candidates[k] = list(dict.fromkeys(candidates[k]))

    # -----------------------------------
    # 6️⃣ primary 결정 (규칙 기반)
    # -----------------------------------
    if candidates["text"]:
        primary = candidates["text"][0]
        source = "text"
    elif candidates["alt"]:
        primary = candidates["alt"][0]
        source = "alt"
    elif candidates["aria"]:
        primary = candidates["aria"][0]
        source = "aria"
    elif candidates["attr"]:
        primary = candidates["attr"][0]
        source = "attr"
    else:
        primary = ""
        source = "none"

    return {
        "primary": primary,
        "source": source,
        "candidates": candidates,
    }

def evaluate_option_intent(segment, container=None):
    """
    옵션 '의도' 판별 (최종본)

    - 반복 구조는 이미 segment 단계에서 확보됨
    - 여기서는 '실제 행동 의도'만 판단
    - wrapper + 모든 하위 인터랙션 노드를 함께 평가

    반환:
    {
        has_intent: bool,
        strong: bool,
        action: bool,
        override_navigation: bool,
        reasons: []
    }
    """

    reasons = []
    strong = False
    action = False

    # ✅ 핵심: segment + 모든 하위 노드까지 확장
    nodes = []
    for n in segment:
        nodes.append(n)
        nodes.extend(n.find_all(True, recursive=True))

    # -------------------------
    # STRONG INTENT (상태 기반)
    # -------------------------
    for n in nodes:
        if (
            n.has_attr("aria-selected")
            or n.has_attr("aria-checked")
            or n.has_attr("aria-pressed")
        ):
            strong = True
            reasons.append("state:aria")

        if n.name == "input" and n.get("type") in {"radio", "checkbox"}:
            strong = True
            reasons.append("input:radio/checkbox")

        role = n.get("role")
        if role in {"radio", "option"}:
            strong = True
            reasons.append(f"role:{role}")

    if strong:
        return {
            "has_intent": True,
            "strong": True,
            "action": False,
            "override_navigation": True,
            "reasons": list(set(reasons)),
        }

    # -------------------------
    # ACTION INTENT (행위 기반)
    # -------------------------
    action_signals = 0

    for n in nodes:
        if n.name == "button":
            action_signals += 2
            reasons.append("tag:button")

        if n.get("role") == "button":
            action_signals += 1
            reasons.append("role:button")

        if n.has_attr("tabindex"):
            action_signals += 1
            reasons.append("tabindex")

        if n.has_attr("onclick"):
            action_signals += 1
            reasons.append("onclick")

        # data-* 힌트
        for attr, val in n.attrs.items():
            if isinstance(val, str):
                low = val.lower()
                matched = [
                    k for k in OPTION_HINT_KEYWORDS if k in low
                ]
                if matched:
                    action_signals += 1
                    reasons.append(
                        f"data-hint:{'/'.join(matched)}"
                    )

    # -------------------------
    # 컨테이너 기반 보조 힌트
    # -------------------------
    if container and container.get("role") == "list":
        listitems = [
            n for n in segment if n.get("role") == "listitem"
        ]
        if len(listitems) == len(segment):
            action_signals += 1
            reasons.append("role:list/listitem")

    if action_signals >= 2:
        action = True

    return {
        "has_intent": action,
        "strong": False,
        "action": action,
        "override_navigation": action,
        "reasons": list(set(reasons)),
    }


def is_navigation_segment(segment):
    hrefs = []
    for n in segment:
        if has_state_signal(n) or n.has_attr("aria-expanded") or n.has_attr("aria-current"):
            return False

        role = n.get("role")
        if role in {"tab", "option", "radio"}:
            return False

        if n.name != "a":
            return False

        href = (n.get("href") or "").strip().lower()
        if not href:
            return False
        hrefs.append(href)

    # ✅ 모든 href가 "외부 이동"처럼 제각각이면 네비 가능성이 큼
    # (옵션 탭은 보통 href가 비슷하거나 동일 패턴)
    if len(set(hrefs)) == len(hrefs):
        return True

    return False



EVENT_ATTRS = {
    "onclick",
    "onmousedown",
    "onmouseup",
    "onkeydown",
    "onkeyup",
    "onchange",
}

def has_state_signal(el):
    return (
        el.has_attr("aria-selected")
        or el.has_attr("aria-checked")
        or el.has_attr("aria-pressed")
    )


def get_interactive_identity(node):
    identity = []

    elements = [node] + list(node.find_all(True, recursive=True))

    # 🔹 상태 신호가 하나라도 있으면 이벤트는 제외
    has_state = any(has_state_signal(el) for el in elements)

    for el in elements:
        # 1️⃣ 인터렉티브 태그
        if el.name in ("button", "a", "input", "select", "textarea", "option"):
            identity.append(f"tag:{el.name}")

        # 2️⃣ role
        role = el.get("role")
        if role:
            identity.append(f"role:{role}")

        # 3️⃣ 이벤트 (상태 없을 때만)
        if not has_state:
            for attr in EVENT_ATTRS:
                if el.has_attr(attr):
                    identity.append(f"attr:{attr}")

        # 4️⃣ 상태
        if el.has_attr("aria-selected"):
            identity.append("attr:aria-selected")
        if el.has_attr("aria-checked"):
            identity.append("attr:aria-checked")
        if el.has_attr("aria-pressed"):
            identity.append("attr:aria-pressed")
        if el.has_attr("aria-expanded"):
            identity.append("attr:aria-expanded")
        if el.has_attr("aria-current"):
            identity.append("attr:aria-current")

        # 5️⃣ 포커스
        if el.has_attr("tabindex"):
            identity.append("attr:tabindex")

        # 6️⃣ 이미지 힌트
        if el.name == "img" or role == "img":
            identity.append("type:img")

    return tuple(identity)


def extract_semantic_text(node):
    """
    옵션 의미 판단에 사용할 '유의미한 텍스트' 추출 (self + descendants)
    - 보이는 텍스트
    - 의미 있는 속성 값(화이트리스트) : self + 후손까지 수집
    """

    parts = []

    # 1) 가시 텍스트
    t = node.get_text(" ", strip=True)
    if t:
        parts.append(t)

    # 2) 의미 있는 속성 (self + descendants)
    SEMANTIC_ATTRS = {
        "aria-label",
        "title",
        "data-value",
        "data-color",
        "data-size",
        "data-testid",
        "for",
        "name",
        "value",
        "id",
    }

    # self 포함해서 전부 훑기
    for el in [node] + list(node.find_all(True, recursive=True)):
        for attr in SEMANTIC_ATTRS:
            if el.has_attr(attr):
                val = el.get(attr)
                if val is None:
                    continue

                # bs4에서 class 같은건 list로 올 수 있으니 처리
                if isinstance(val, (list, tuple)):
                    val = " ".join(map(str, val))
                else:
                    val = str(val)

                val = val.strip()
                if val:
                    parts.append(val)

    blob = " ".join(parts).lower()

    # 3) "actual_color-blue" 같은 것에서 토큰 분해도 같이 제공 (매칭률 증가)
    #    -> actual color blue / actual_color blue / actual-color blue
    blob = re.sub(r"[_\-:/]+", " ", blob)

    # 공백 정리
    blob = re.sub(r"\s+", " ", blob).strip()
    return blob


def evaluate_optionness(segment, container=None):
    if is_navigation_segment(segment):
        return {
            "is_optionlike": False,
            "details": {"reason": "navigation"},
        }

    intent = evaluate_option_intent(segment, container)

    if not intent.get("has_intent"):
        return {
            "is_optionlike": False,
            "details": intent,
        }

    return {
        "is_optionlike": True,
        "details": intent,
    }




# def should_skip_container(container):
#     """
#     return:
#         (skip: bool, reason: str)
#     """
#     children = container.find_all(recursive=False)

#     # 1️⃣ 인터랙션 없음
#     has_interaction = False
#     for c in children:
#         if c.find(
#             ["button", "input", "select", "option"],
#             recursive=True
#         ):
#             has_interaction = True
#             break

#     if not has_interaction:
#         return True, "no-interaction-in-children"

#     # 2️⃣ 키워드 기반
#     blob = " ".join(
#         " ".join(c.get("class", [])) + " " + (c.get("id") or "")
#         for c in children
#     ).lower()

#     for k in {
#         "review", "rating",
#         "recommend", "related",
#         "carousel", "gallery"
#     }:
#         if k in blob:
#             return True, f"keyword:{k}"

#     return False, ""

def iter_containers_postorder(root):
    stack = [(root, False)]
    out = []

    while stack:
        node, visited = stack.pop()
        if not hasattr(node, "find_all"):
            continue

        if visited:
            out.append(node)
        else:
            stack.append((node, True))
            for ch in node.find_all(True, recursive=False)[::-1]:
                stack.append((ch, False))

    print(f"[LOG] post-order containers count = {len(out)}")
    return out

def is_repeating_pair(a, b):
    
    id_a = get_interactive_identity(a)
    id_b = get_interactive_identity(b)
    
    print("    [IDENTITY CHECK]")
    print(f"      A: <{a.name}> class={a.get('class')}")
    print(f"         identity={id_a}")
    print(f"      B: <{b.name}> class={b.get('class')}")
    print(f"         identity={id_b}")
    
    if a.name != b.name:
        return False

    if id_a != id_b:
        return False

    if a.get("class") and b.get("class"):
        score = class_overlap_score(a, b)
        print(f"  class overlap score = {score:.2f}")
        if score < 0.3:
            return False

    # print("  ✅ MATCH")
    return True




def get_dom_level(node):
    level = 0
    p = node
    while p and getattr(p, "parent", None):
        level += 1
        p = p.parent
    return level



def find_repeating_structures_bottom_up(root):
    segments = []
    claimed_nodes = set()

    containers = iter_containers_postorder(root)

    print("\n[LOG] === Bottom-up repeating structure scan START ===")

    for idx, container in enumerate(containers):
        tag = container.name
        cls = " ".join(container.get("class", []) or [])
        print(f"\n[SCAN {idx:04d}] <{tag}> class='{cls}'")

        # -------------------------------------------------
        # 1️⃣ 직계 자식 수집 (visible only)
        # -------------------------------------------------
        children = [
            c for c in container.find_all(True, recursive=False)
            if is_visible(c)
        ]
        print(f"  - visible children : {len(children)}")
        for k, c in enumerate(children):
            print(f"      child[{k}] tag={c.name} class={c.get('class')}")

        if len(children) < 2:
            print("  - skip: children < 2")
            continue

        # -------------------------------------------------
        # 2️⃣ claimed 필터
        # -------------------------------------------------
        before = len(children)
        children = [c for c in children if id(c) not in claimed_nodes]
        removed = before - len(children)

        if removed:
            print(f"  - filtered claimed children : {removed} removed")

        if len(children) < 2:
            print("  - skip: children < 2 after claimed-filter")
            continue

        # -------------------------------------------------
        # 3️⃣ 형제 반복 검사
        # -------------------------------------------------
        i = 0
        while i < len(children) - 1:
            c1 = children[i]
            c2 = children[i + 1]

            print(f"\n    [PAIR CHECK] {i} vs {i+1}")
            print(f"      A: <{c1.name}> class={c1.get('class')}")
            print(f"      B: <{c2.name}> class={c2.get('class')}")

            if not is_repeating_pair(c1, c2):
                print(
                    f"    [NO MATCH] {i} vs {i+1} "
                    f"({c1.name} , {c2.name})"
                )
                i += 1
                continue

            print(
                f"    [MATCH START] idx={i} tag={c1.name}"
            )

            # -------------------------------------------------
            # 4️⃣ segment 확장
            # -------------------------------------------------
            seg = [c1, c2]
            j = i + 2

            while j < len(children):
                print(f"      [EXTEND CHECK] {j-1} vs {j}")
                if is_repeating_pair(children[j - 1], children[j]):
                    seg.append(children[j])
                    j += 1
                else:
                    break

            print(
                f"    [SEGMENT FOUND] len={len(seg)} "
                f"tags={[n.name for n in seg]}"
            )

            # 🔴 실체 증거: segment 내부 노드 출력
            for si, n in enumerate(seg):
                print(
                    f"        seg[{si}] tag={n.name} "
                    f"class={n.get('class')}"
                )
                print(
                    f"          html={n.prettify()[:200].replace(chr(10),' ')}"
                )

            # -------------------------------------------------
            # 5️⃣ 옵션 여부 판정
            # -------------------------------------------------
            result = evaluate_optionness(seg, container)

            print(f"    [OPTION CHECK] is_optionlike={result.get('is_optionlike')}")
            if not result.get("is_optionlike"):
                print("    [DROP] not optionlike segment")
                i = j
                continue

            # -------------------------------------------------
            # 6️⃣ segment 확정
            # -------------------------------------------------
            segments.append({
                "container": container,
                "segment": seg,
                "level": get_dom_level(container),
                "option_result": result,
            })

            for n in seg:
                claimed_nodes.add(id(n))

            print(
                f"    [CLAIMED] node_ids={[id(n) for n in seg]}"
            )

            i = j

    print("\n[LOG] === Bottom-up repeating structure scan END ===")
    print(f"[LOG] total segments found = {len(segments)}")

    return segments



from bs4.element import NavigableString, Tag

def get_visible_text(node):
    if not is_visible(node):
        return ""

    parts = []
    for desc in node.descendants:
        if isinstance(desc, NavigableString):
            parent = desc.parent
            if not parent or parent.get("aria-hidden") == "true":
                continue
            if is_visible(parent):
                t = str(desc).strip()
                if t:
                    parts.append(t)

    return re.sub(r"\s+", " ", " ".join(parts)).strip()



if __name__ == "__main__":
    from bs4 import BeautifulSoup

    TARGET_FILE = "test_html/product_detail.html"

    OPTION_HINTS = ["color", "black"]

    # =================================================
    # 0️⃣ HTML 로드
    # =================================================
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # =================================================
    # 1️⃣ BODY 기준 반복 구조 탐색
    # =================================================
    root = soup.body if soup.body else soup
    segments = find_repeating_structures_bottom_up(root)

    print("\n[SYSTEM] 🧪 옵션 구조 후보 수집")
    print("=" * 120)

    option_candidates = []
    
    # =================================================
    # 2️⃣ 구조 후보 → 옵션 판별
    # =================================================
    for idx, info in enumerate(segments, start=1):
        seg = info["segment"]
        container = info.get("container")

        result = info["option_result"]

        # -------------------------------------------------
        # 옵션 값 후보 추출
        # -------------------------------------------------
        extracted_values = []
        for n in seg:
            extracted = extract_option_value_candidates(n)
            if extracted.get("primary"):
                extracted_values.append(extracted)

        if not extracted_values:
            continue

        # diversity score
        primary_values = [v["primary"] for v in extracted_values]
        diversity_score = value_diversity_score(primary_values)

        option_candidates.append({
            "index": idx,
            "container": container,
            "segment": seg,
            "result": result,
            "values": extracted_values,
            "diversity_score": diversity_score,
        })

    # =================================================
    # 3️⃣ 우선순위 정렬 (level 제거)
    # =================================================
    # option_candidates = sorted(
    #     option_candidates,
    #     key=lambda x: (
    #         -x["result"]["details"].get("confidence", 0.0),
    #         -x["diversity_score"],
    #     )
    # )[:5]

    # =================================================
    # 4️⃣ 🔥 LLM 옵션 그룹 필터
    # =================================================
    VALUE_GROUPS = {}
    group_map = {}

    for i, cand in enumerate(option_candidates, start=1):
        gid = f"{i:02d}"
        VALUE_GROUPS[gid] = [v["primary"] for v in cand["values"]]
        group_map[gid] = cand

    print("\n[SYSTEM] 🧠 LLM 전달 VALUE_GROUPS")
    print("=" * 120)
    for gid, values in VALUE_GROUPS.items():
        print(f"  [{gid}]")
        for v in values:
            print(f"    - {v}")

    selected_group_ids = pick_option_groups_by_llm(
        VALUE_GROUPS,
        OPTION_HINTS
    )

    final_option_candidates = [
        group_map[g]
        for g in selected_group_ids
        if g in group_map
    ]

    # =================================================
    # 5️⃣ 최종 출력
    # =================================================
    print("\n[SYSTEM] 🧪 최종 옵션 구조 후보 (LLM 필터 통과)")
    print("=" * 120)

    for cand in final_option_candidates:
        seg = cand["segment"]
        result = cand["result"]

        print(f"\n[SEGMENT #{cand['index']}]")
        print(f"  - len        : {len(seg)}")
        print(f"  - tags       : {[n.name for n in seg]}")
        print(f"  - optionlike : True")

        details = result.get("details", {})
        print(
            f"  - intent     : strong={details.get('strong')} "
            f"action={details.get('action')}"
        )
        print(f"  - reasons    : {details.get('reasons')}")
        print(f"  - confidence : {details.get('confidence')}")
        print(f"  - confHints  : {details.get('confidence_hints')}")

        print(f"  - diversity_score : {cand['diversity_score']:.3f}")

        print("  - visible text:")
        for i, n in enumerate(seg):
            txt = get_visible_text(n)
            print(f"      [{i}] {txt if txt else '(no visible text)'}")

        debug = result.get("debug", {})
        rep_infos = debug.get("rep_infos", [])
        if rep_infos:
            print("  - interactive fingerprint:")
            for i, r in enumerate(rep_infos):
                print(f"      [{i}] tag={r['tag']}")
                print(f"          text='{r['text']}'")
                print(f"          identity={r['identity']}")

        print("  - option values:")
        for i, v in enumerate(cand["values"]):
            print(f"      [{i}] {v['primary']} (source={v['source']})")

