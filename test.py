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
    if node.has_attr('hidden'):
        return False

    classes = node.get('class', []) or []
    classes_lower = [c.lower() for c in classes]

    # 🔥 정확히 "숨김용 클래스"일 때만 숨김 처리
    HIDDEN_CLASS_EXACT = {
        "hidden",
        "hide",
        "sr-only",
        "visually-hidden",
        "dn",   # ← 단독 클래스일 때만
    }

    for c in classes_lower:
        if c in HIDDEN_CLASS_EXACT:
            return False

    # inline style
    style = node.get('style', '').lower().replace(" ", "")
    if 'display:none' in style or 'visibility:hidden' in style:
        return False

    return True


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
        
        "node": node,
        "selector": build_click_selector(node),
        "fingerprint": build_node_fingerprint(node),
    }

def evaluate_option_intent(segment, container=None):
    """
    옵션 '의도' 판별 (안정 최종본)
    """

    reasons = []
    strong = False
    action = False

    # -------------------------------------------------
    # 1️⃣ segment + 모든 하위 노드 확장
    # -------------------------------------------------
    nodes = []
    for n in segment:
        nodes.append(n)
        nodes.extend(n.find_all(True, recursive=True))

    # -------------------------------------------------
    # 2️⃣ STRONG INTENT (상태 기반)
    # -------------------------------------------------
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

    # -------------------------------------------------
    # 3️⃣ ACTION INTENT
    # -------------------------------------------------
    action_signals = 0

    # 🔥 (A) segment 레벨 링크 옵션 감지 (가장 중요)
    for n in segment:
        a = n.find("a", href=True)
        if a:
            action_signals += 2
            reasons.append("segment:a-link")
            break

    # 🔥 (B) 일반 인터랙션 요소
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
                    reasons.append(f"data-hint:{'/'.join(matched)}")

    # -------------------------------------------------
    # 4️⃣ 컨테이너 보조 신호
    # -------------------------------------------------
    if container and container.get("role") == "list":
        listitems = [
            n for n in segment if n.get("role") == "listitem"
        ]
        if len(listitems) == len(segment):
            action_signals += 1
            reasons.append("role:list/listitem")

    # -------------------------------------------------
    # 5️⃣ 최종 판정
    # -------------------------------------------------
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
    has_option_semantics = False

    for n in segment:
        # 🔥 옵션 의미 텍스트 감지
        txt = extract_semantic_text(n)
        if any(k in txt for k in [
            "color", "size", "ml", "gb", "charcoal", "blue", "white"
        ]):
            has_option_semantics = True

        # 기존 로직
        a = n.find("a")
        if not a:
            return False

        href = (a.get("href") or "").strip().lower()
        if not href:
            return False
        hrefs.append(href)

    # 🔥 옵션 의미가 있으면 네비게이션 아님
    if has_option_semantics:
        return False

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

    return tuple(sorted(identity))



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

def segment_is_site_setting_ui(segment):
    """
    쿠키 동의 / 사이트 설정 / 환경설정 UI 제거
    상품 옵션과 구조적으로 다른 '사이트 제어 UI' 감지
    """

    # 전체 노드 확장
    nodes = []
    for n in segment:
        nodes.append(n)
        nodes.extend(n.find_all(True, recursive=True))

    checkbox_count = 0
    toggle_like = 0
    cookie_keyword_hit = 0
    product_signal = 0

    for n in nodes:
        tag = n.name

        # 1️⃣ 설정 토글 핵심 구조
        if tag == "input" and n.get("type") == "checkbox":
            checkbox_count += 1

        # 2️⃣ 토글/스위치 계열 클래스
        cls = " ".join(n.get("class", [])).lower()
        if any(k in cls for k in ["toggle", "switch", "consent", "preference"]):
            toggle_like += 1

        # 3️⃣ 쿠키/프라이버시 키워드
        text = (n.get_text(" ", strip=True) or "").lower()
        if any(k in text for k in [
            "cookie", "privacy", "consent", "marketing cookies",
            "functional cookies", "performance cookies", "tracking"
        ]):
            cookie_keyword_hit += 1

        # 4️⃣ 상품 신호 (있으면 설정 UI 아닐 확률 상승)
        if tag == "img" and n.get("src"):
            product_signal += 1
        if tag == "a" and n.get("href"):
            href = n.get("href", "")
            if any(p in href.lower() for p in ["product", "item", "sku"]):
                product_signal += 1

    # -------------------------
    # 🎯 판정 로직
    # -------------------------

    # 체크박스 여러 개 + 토글 UI 구조 + 쿠키 키워드
    if checkbox_count >= 2 and (toggle_like >= 1 or cookie_keyword_hit >= 1):
        return True

    # 체크박스가 반복 구조 핵심이면 거의 확정
    if checkbox_count >= len(segment):
        return True

    return False


def segment_is_carousel_control(segment):
    """
    슬라이더/캐러셀 화살표 컨트롤 제거
    (Splide, Swiper 등)
    """

    nav_keywords = {"prev", "next", "previous", "slide"}
    class_keywords = {"splide", "swiper", "carousel", "arrow", "slider"}

    hit = 0

    for n in segment:
        cls = " ".join(n.get("class", [])).lower()
        text = (n.get_text(" ", strip=True) or "").lower()

        if any(k in cls for k in class_keywords):
            hit += 1

        if any(k in text for k in nav_keywords):
            hit += 1

        if n.has_attr("aria-controls"):
            val = n.get("aria-controls", "").lower()
            if "track" in val or "slide" in val:
                hit += 1

    return hit >= 2


def evaluate_optionness(segment, container=None):
    
    # 🔴 0️⃣ 사이트 설정 / 쿠키 / 환경설정 UI 제거 (최우선)
    if segment_is_site_setting_ui(segment):
        return {
            "is_optionlike": False,
            "details": {"reason": "site_setting_ui"},
        }
        
    # 🔴 0.5️⃣ 캐러셀/슬라이더 컨트롤 제거  ← 여기 추가
    if segment_is_carousel_control(segment):
        return {"is_optionlike": False, "details": {"reason": "carousel_control"}}

    # 🔴 1️⃣ 상품 엔티티 리스트 제거 (추천상품, 카드 리스트 등)
    if segment_is_product_list(segment):
        return {
            "is_optionlike": False,
            "details": {"reason": "product_entity_block"},
        }

    # 🔴 2️⃣ 네비게이션 / 메뉴 / 탭 UI 제거
    if is_navigation_segment(segment):
        return {
            "is_optionlike": False,
            "details": {"reason": "navigation"},
        }

    # 🟢 3️⃣ 여기서부터 진짜 옵션 후보만 남음
    intent = evaluate_option_intent(segment, container)

    if intent.get("has_intent"):
        return {
            "is_optionlike": True,
            "details": intent,
        }

    return {
        "is_optionlike": False,
        "details": intent,
    }




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

def is_product_entity(node):
    text = node.get_text(" ", strip=True).lower()
    html = str(node).lower()

    # 1️⃣ 상품 식별자 (가장 강력)
    if node.find(attrs={"data-articlecode": True}):
        return True
    if node.find(attrs={"data-product-id": True}):
        return True
    if node.find(attrs={"data-sku": True}):
        return True

    # 2️⃣ 가격
    if re.search(r"\b(₩|\$|€|price|krw|usd)\b", text):
        return True

    # 3️⃣ 리뷰 / 평점
    if re.search(r"\b(review|rating|star)\b", text):
        return True

    # 4️⃣ 상품명 구조
    if node.find(["h2", "h3", "h4"]):
        return True

    # 5️⃣ 구매행동
    if re.search(r"add to bag|wishlist|quick shop|cart", html):
        return True

    return False

def segment_is_product_list(segment):
    hits = 0
    for n in segment:
        flag = is_product_entity(n)
        print(f"[PRODUCT_ENTITY_CHECK] tag={n.name} flag={flag}")
        if flag:
            hits += 1
    print(f"[PRODUCT_ENTITY_HITS] {hits} / {len(segment)}")
    return hits >= max(1, len(segment)//3)



if __name__ == "__main__":
    from bs4 import BeautifulSoup

    TARGET_FILE = "test_html/product_detail.html"
    OPTION_HINTS = ["COLOR", "NATURAL", "Size", "XXS"]
    PRODUCT_TITLE = "Sherpa fleece toggle jacket"

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
        
        if len(set(primary_values)) < len(primary_values):
            print(f"[DROP] duplicate values detected → {primary_values}")
            continue

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
        OPTION_HINTS,
        PRODUCT_TITLE
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
    
    from models import OptionNodeRef  # 실제 위치에 맞게

    option_node_groups = {}

    for cand in final_option_candidates:
        seg = cand["segment"]
        group_name = guess_group_name(cand)
        
        node_refs = []
        
        for idx, val in enumerate(cand["values"]):
            ref = OptionNodeRef(
            value=val["primary"],
            selector=val["selector"],
            fingerprint=val["fingerprint"],
            depth_index=len(option_node_groups),
            meta={
                "source": val["source"]
            }
        )
        node_refs.append(ref)
        
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
            
    option_node_groups[group_name] = node_refs

