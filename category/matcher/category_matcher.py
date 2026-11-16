# final_matcher_with_log.py
# ============================================================
# Category Matching - Final Implementation (template_key based)
# ============================================================

import logging, re, os
import csv
from utils.path import p
from typing import Dict, List, Optional
from .synonym_loader import load_synonym_index, expand_keywords_with_synonyms, get_synonym_group_weight, get_group_max_weights

# --------------------
# Logging Config
# --------------------
logging.basicConfig(
    level=logging.DEBUG,   # DEBUG / INFO
    format="[%(levelname)s] %(message)s"
)
log = logging.getLogger("category_matcher")

# --------------------
# Constants
# --------------------
NAME_BONUS = 10.0
OPTION_BONUS = 1.0
TAIL_MATCH_BONUS = 1.0
MAIN_KEYWORD_THRESHOLD = 3.0

TARGET_GROUPS = {
    "MEN": ["남성", "남자", "남자용", "남성용", "men", "male"],
    "WOMEN": ["여성", "여자", "여자용", "여성용", "women", "female", "ladies"],
    "KIDS": ["어린이", "키즈", "아동", "kids", "child"],
    "BABY": ["유아", "베이비", "아기", "baby"]
}


# ============================================================
# Utils
# ============================================================

def extract_keywords_from_template(template_key: str) -> List[str]:
    """
    template_key를 공백 기준으로 분리
    예: '남성 민소매 티셔츠' → ['남성', '민소매', '티셔츠']
    """
    return [k for k in template_key.split() if k]


# ============================================================
# Keyword Weight (Precompute)
# ============================================================

def compute_keyword_weight(keyword: str, categories_by_market: Dict[str, str]) -> float:
    """
    keyword의 구조적 중요도 계산
    - depth 평균
    - suffix count
    ⚠️ bonus는 절대 포함하지 않음
    """
    depth_scores = []
    suffix_count = 0

    for market, path in categories_by_market.items():
        steps = [s.strip().replace(" ", "") for s in path.split("»")]

        for idx, step in enumerate(steps):
            if keyword in step:
                depth_scores.append(idx + 1)
                log.debug(
                    f"[WEIGHT-HIT] keyword='{keyword}' | market='{market}' | "
                    f"step='{step}' | depth={idx+1}"
                )
                break

        if steps and steps[-1].endswith(keyword):
            suffix_count += 1
            log.debug(
                f"[WEIGHT-SUFFIX] keyword='{keyword}' | market='{market}' | last='{steps[-1]}'"
            )

    if not depth_scores:
        log.debug(f"[WEIGHT-EMPTY] keyword='{keyword}' → weight=1.0")
        return 1.0

    weight = (sum(depth_scores) / len(depth_scores)) + suffix_count
    log.debug(
        f"[WEIGHT-FINAL] keyword='{keyword}' | "
        f"depth_avg={sum(depth_scores)/len(depth_scores):.3f} | "
        f"suffix={suffix_count} | weight={weight:.3f}"
    )
    return max(1.0, weight)




def normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", s)


def extract_category_tokens(
    categories: Dict[str, str],
    template_words: List[str]
) -> List[str]:
    tokens = set()

    template_words = [
        w.strip().replace(" ", "")
        for w in template_words
        if w and len(w.strip()) >= 2
    ]

    for path in categories.values():
        steps = [s.strip() for s in re.split(r"[»>/]", path) if s.strip()]

        for step in steps:
            step_ns = step.replace(" ", "")

            # 1) step 자체
            if len(step_ns) >= 2 and step_ns.lower() != "basic":
                tokens.add(step_ns)

            # 2) 구분자 분리
            for part in re.split(r"[\s/,&·\-()]+", step):
                p = part.strip().replace(" ", "")
                if len(p) >= 2 and p.lower() != "basic":
                    tokens.add(p)

            # 3) ⭐ 핵심: template 단어가 step 내부에 포함되면 토큰 인정
            for w in template_words:
                if w in step_ns:
                    tokens.add(w)

    return list(tokens)



def resolve_template_keywords(template_key: str, categories: Dict[str, str]) -> List[str]:
    # 🎯 특정 타겟에 대해 상세 프로세스 로그 활성화
    is_target = ("여자용라운드넥티" in template_key or "여자 라운드넥 긴팔티셔츠" in template_key)

    # 1) 카테고리 토큰 수집 (기존 동일)
    atom_tokens = set()
    for path in categories.values():
        steps = re.split(r"[»>]", path)
        for step in steps:
            parts = re.split(r"[ /&·\-()]+", step)
            for p in parts:
                token = p.strip()
                if len(token) >= 2 and token.lower() not in {"basic"}:
                    atom_tokens.add(token)

    all_expanded_keywords = []

    def expand_word(word: str, level: int = 0):
        if not word or len(word) < 1:
            return
        
        indent = "  " * level
        
        # 이미 수집된 키워드라면 중복 처리 방지
        if word in all_expanded_keywords:
            return
        
        # ✨ [의도 반영] 현재 단계의 단어(원본/중간덩어리/조각)를 즉시 수집
        all_expanded_keywords.append(word)
        
        if is_target:
            log.debug(f"{indent}[EXPAND-PROCESS] Level {level} | 수집됨: '{word}'")

        # 현재 단어 내부에 포함된 토큰 찾기 (단어 자신 제외)
        found_tokens = [t for t in atom_tokens if t in word and t != word]
        found_tokens.sort(key=len, reverse=True)

        if found_tokens:
            # 가장 긴 토큰을 기준으로 먼저 쪼개기
            token = found_tokens[0]
            pattern = f"({re.escape(token)})"
            
            # maxsplit=1로 설정하여 한 번에 하나씩만 쪼개며 중간 과정을 추적
            pieces = [p for p in re.split(pattern, word, maxsplit=1) if p]
            
            if is_target:
                log.debug(f"{indent}  ㄴ 🔪 '{word}'를 토큰 '{token}' 기준으로 분해 -> {pieces}")

            for piece in pieces:
                # 쪼개진 조각(왼쪽 잔여물, 토큰 자체, 오른쪽 잔여물)을 다시 재귀적으로 분해
                expand_word(piece, level + 1)

    # 2) 실행 및 로그 출력
    if is_target:
        log.debug(f"\n{'='*60}\n[TARGET-DEBUG] 분해 프로세스 시작: '{template_key}'\n{'='*60}")

    for word in template_key.split():
        expand_word(word)

    # 3) 중복 제거 (순서 유지)
    final = []
    seen = set()
    for k in all_expanded_keywords:
        if k not in seen:
            seen.add(k)
            final.append(k)

    if is_target:
        log.debug(f"\n[TARGET-RESULT] 최종 추출된 모든 키워드 셋:")
        log.debug(f" -> {final}")
        log.debug(f"{'='*60}\n")

    return final

# ============================================================
# Category Matching
# ============================================================

def match_category_from_json(
    category_data: List[dict],
    product_name: str,
    option_names: List[str],
    detail_text: str
) -> Optional[dict]:

    product_text = product_name or ""
    option_text = " ".join(option_names or [])
    detail_text = detail_text or ""

    log.debug("========================================")
    log.debug("[MATCH] 카테고리 매칭 시작")
    log.debug(f"[MATCH] 상품명: {product_text}")
    log.debug(f"[MATCH] 옵션명: {option_text}")
    log.debug("========================================")

    results = []
    
    global_weight_map = build_global_keyword_weight_map(category_data)

    for item in category_data:
        template_key = item["template_key"]
        categories = item["categories"]
        
        # -------------------------------------------------------
        # 🔥 [추가] 필수 대상 키워드 상충 검사 (Hard Filter)
        # -------------------------------------------------------
        is_conflict = False
        
        # 상품명과 옵션명에서 언급된 성별/대상 파악
        found_in_product = [group for group, kws in TARGET_GROUPS.items() if any(kw in product_text.lower() for kw in kws)]
        
        # 카테고리(template_key)에서 언급된 성별/대상 파악
        found_in_category = [group for group, kws in TARGET_GROUPS.items() if any(kw in template_key for kw in kws)]

        # [상충 판단 로직]
        # 상품명에도 대상이 명시되어 있고, 카테고리에도 대상이 명시되어 있는데 
        # 두 대상이 서로 다를 경우에만 상충(Conflict)으로 판단!
        if found_in_product and found_in_category:
            # 두 리스트를 비교하여 겹치는 게 하나도 없다면 상충
            if not set(found_in_product).intersection(set(found_in_category)):
                # 단, '공용' 키워드가 상품명이나 카테고리에 있다면 상충에서 제외하는 예외처리 가능
                if "공용" not in product_text and "UNISEX" not in template_key:
                    is_conflict = True

        if is_conflict:
            log.debug(f"[FILTER] 대상 상충 발생으로 제외: 상품({found_in_product}) vs 카테고리({found_in_category})")
            continue # 점수 계산 안 하고 바로 다음 카테고리로 패스

        # 🔑 template_key 기반 키워드 추출
        keywords = resolve_template_keywords(template_key, categories)
        keywords = expand_keywords_with_synonyms(keywords)

        synonym_index = load_synonym_index()

        group_max_weight_map = get_group_max_weights(
            keywords,
            global_weight_map,
            synonym_index
        )

        keyword_weight = {}
        for kw in keywords:
            if kw in group_max_weight_map:
                keyword_weight[kw] = group_max_weight_map[kw]
            else:
                keyword_weight[kw] = global_weight_map.get(kw, 1.0)

        log.debug("----------------------------------------")
        log.debug(f"[TEMPLATE] {template_key}")
        log.debug(f"[KEYWORDS] {keywords}")

        total_score = 0.0
        matched_main_keywords = 0

        for keyword, weight in keyword_weight.items():
            log.debug(f"[KEYWORD-WEIGHT] '{keyword}' = {weight:.3f}")

            matched = False
            source = None

            # 1) 매칭 판단
            if keyword in product_text:
                matched = True
                source = "상품명"
            elif keyword in option_text:
                matched = True
                source = "옵션명"
            elif keyword in detail_text:
                matched = True
                source = "상세설명"

            if not matched:
                continue

            # 2) 주키워드 판별
            is_main = weight > MAIN_KEYWORD_THRESHOLD
            if is_main:
                matched_main_keywords += 1

            # 3) 🔥 모든 bonus는 주키워드에만 적용
            bonus = 0.0
            if is_main:
                if source == "상품명":
                    bonus = NAME_BONUS
                elif source == "옵션명":
                    bonus = OPTION_BONUS
                elif source == "상세설명":
                    bonus = 0.0  # 유지 (확장 가능)

            keyword_score = weight + bonus
            total_score += keyword_score

            log.debug(
                f"[KEYWORD] '{keyword}' | weight={weight:.3f} | "
                f"source={source} | bonus={bonus} | "
                f"score={keyword_score:.3f} | "
                f"{'MAIN' if is_main else 'SUB'}"
            )


        if matched_main_keywords == 0:
            log.debug("[DROP] 주키워드 없음 → 제외")
            continue

        log.debug(f"[RESULT] total_score={total_score:.3f}")

        results.append({
            "template_key": template_key,
            "score": total_score,
            "categories": categories
        })

    if not results:
        log.warning("[MATCH] 유효한 카테고리 없음")
        return None

    results.sort(key=lambda x: x["score"], reverse=True)

    best_score = results[0]["score"]
    best_candidates = [
        r for r in results
        if abs(r["score"] - best_score) < 1e-6
    ]

    log.debug("========================================")
    log.debug(f"[MATCH] 최고 점수: {best_score:.3f}")
    log.debug(f"[MATCH] 최고 점수 후보 수: {len(best_candidates)}")

    for idx, cand in enumerate(best_candidates, 1):
        log.debug(
            f"[MATCH-CANDIDATE {idx}] "
            f"template_key='{cand['template_key']}' | "
            f"score={cand['score']:.3f}"
        )

    log.debug("========================================")

    # 🔽 반환은 1개가 아니라 묶음
    return {
        "score": best_score,
        "candidates": best_candidates,
        "detail_text": detail_text,
    }
    
def build_global_keyword_weight_map(category_data: list) -> dict:
    """
    모든 template_key / categories를 기준으로
    keyword별 평균 weight를 계산한 전역 맵 생성
    """
    from collections import defaultdict

    bucket = defaultdict(list)

    for item in category_data:
        template_key = item.get("template_key", "")
        categories = item.get("categories", {})

        # template_key에서 키워드 추출
        keywords = template_key.split()

        for kw in keywords:
            w = compute_keyword_weight(kw, categories)
            bucket[kw].append(w)

    # 평균 계산
    avg_map = {}
    for kw, values in bucket.items():
        avg_map[kw] = sum(values) / len(values)

    return avg_map

def normalize_smartstore_path(path: str) -> str:
    if not path or not isinstance(path, str):
        return path

    # 스마트스토어/네이버 카테고리 구분자 통일
    path = (
        path.replace("»", ">")
            .replace("›", ">")
    )

    parts = [p.strip() for p in path.split(">") if p.strip()]
    return " > ".join(parts)


def get_smartstore_category_code(category_path: str) -> str | None:

    if not category_path or not isinstance(category_path, str):
        return None

    # 1) path 정규화 + depth 분해
    normalized = normalize_smartstore_path(category_path)
    parts = [x.strip() for x in normalized.split(">") if x.strip()]
    if len(parts) < 2:
        return None

    target = parts[:4]  # 최대 세분류까지만 비교

    # 2) CSV 로딩
    csv_path = p("data", "smartstore_categories.csv")
    if not os.path.exists(csv_path):
        return None

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter="\t")

        for row in reader:
            if len(row) < 5:
                continue

            code = (row[0] or "").strip()
            depths = [(row[i] or "").strip() for i in range(1, 5)]

            matched = True
            for i, t in enumerate(target):
                if depths[i] != t:
                    matched = False
                    break

            if matched:
                return code or None

    return None


from llm.llm_client import request_llm, get_prompt
from llm.llm_category_refiner import llm_pick_best_category

# category/matcher/category_matcher.py

def resolve_category_with_llm(
    *,
    product_name: str,
    option_names: list[str],
    detail_text: str,
    match_result: dict,
    image_urls: list[str],
) -> dict:
    """
    LLM 기반 카테고리 최종 선택
    - ProductItem 직접 참조 금지
    - 필요한 값은 모두 명시적으로 전달
    """

    log.debug("========== [LLM CATEGORY RESOLVE START] ==========")
    log.debug("[INPUT] product_name = %s", product_name)
    log.debug("[INPUT] option_names = %s", option_names)
    log.debug("[INPUT] image_urls = %s", image_urls)

    # --------------------------------------------------
    # 1) RAW 상세설명 검증
    # --------------------------------------------------
    raw_detail = detail_text or ""

    log.debug("========== [DETAIL RAW CHECK] ==========")
    log.debug("[DETAIL] type = %s", type(raw_detail))
    log.debug("[DETAIL] length = %s", len(raw_detail) if isinstance(raw_detail, str) else "N/A")
    log.debug("[DETAIL] RAW PREVIEW ↓↓↓\n%s", raw_detail[:500])
    log.debug("=======================================")

    filtered_detail = ""

    # --------------------------------------------------
    # 2) 상세설명 정제 (조건부 1회)
    # --------------------------------------------------
    if not isinstance(raw_detail, str):
        log.debug("[DETAIL] ❌ raw_detail 문자열 아님 → 스킵")

    elif not raw_detail.strip():
        log.debug("[DETAIL] ❌ raw_detail 빈 문자열 → 스킵")

    elif len(raw_detail.strip()) < 30:
        log.debug("[DETAIL] ❌ raw_detail 너무 짧음 (%d) → 스킵", len(raw_detail.strip()))

    else:
        log.debug("[DETAIL] ✅ 정제 조건 통과 → LLM 호출")

        prompt = get_prompt("CATEGORY_DETAIL_FILTER")
        log.debug("[DETAIL] FILTER PROMPT PREVIEW ↓↓↓\n%s", prompt[:300])

        filtered_detail = request_llm(
            f"{prompt}\n\n[상품 상세설명]\n{raw_detail}"
        ) or ""

        log.debug("========== [DETAIL FILTER RESULT] ==========")
        log.debug("[DETAIL] FILTERED length = %d", len(filtered_detail))
        log.debug("[DETAIL] FILTERED PREVIEW ↓↓↓\n%s", filtered_detail[:500])
        log.debug("============================================")

    # --------------------------------------------------
    # 3) 후보 로그
    # --------------------------------------------------
    candidates = match_result.get("candidates", [])
    log.debug("[CANDIDATES] count = %d", len(candidates))

    for i, c in enumerate(candidates, 1):
        log.debug(
            "[CANDIDATE %d] %s | score=%s",
            i,
            c.get("template_key"),
            c.get("score"),
        )

    if len(candidates) < 2:
        log.debug("[EXIT] 후보 1개 → LLM 미사용")
        return {
            "final": candidates[0] if candidates else None,
            "candidates": candidates,
            "filtered_detail_text": filtered_detail,
            "source": "rule",
        }

    # --------------------------------------------------
    # 4) LLM 최종 선택
    # --------------------------------------------------
    picked = llm_pick_best_category(
        product_name=product_name,
        option_names=option_names,
        filtered_description=filtered_detail,
        candidates=candidates,
        image_urls=image_urls,
    )

    log.debug("[LLM RESULT] picked = %s", picked)

    if not picked:
        log.debug("[LLM RESULT] ❌ 선택 실패")
        return {
            "final": None,
            "candidates": candidates,
            "filtered_detail_text": filtered_detail,
            "source": "llm_fail",
        }

    final = next(
        (c for c in candidates if c.get("template_key") == picked),
        None,
    )

    if not final:
        log.debug("[LLM RESULT] ❌ picked key 불일치")
        return {
            "final": None,
            "candidates": candidates,
            "filtered_detail_text": filtered_detail,
            "source": "llm_mismatch",
        }

    log.debug(
        "[FINAL] template_key=%s score=%s",
        final.get("template_key"),
        final.get("score"),
    )

    log.debug("========== [LLM CATEGORY RESOLVE END] ==========")

    return {
        "final": final,
        "candidates": candidates,
        "filtered_detail_text": filtered_detail,
        "source": "llm",
    }


# ============================================================
# Example
# ============================================================

if __name__ == "__main__":
    category_data = [
        {
            "template_key": "스웨터 남성티셔츠",
            "categories": {
                "11번가": "해외직구 » 의류/언더웨어 » 남성티셔츠 » 민소매티셔츠",
                "쿠팡": "패션의류잡화 » 남성패션 » 남성의류 » 티셔츠 » 남성 민소매/나시"
            }
        },
        {
            "template_key": "남성 반팔 티셔츠",
            "categories": {
                "11번가": "해외직구 » 의류/언더웨어 » 남성티셔츠 » 반팔티셔츠",
                "쿠팡": "패션의류잡화 » 남성패션 » 남성의류 » 티셔츠 » 반팔"
            }
        }
    ]

    result = match_category_from_json(
        category_data,
        product_name="남성 민소매 티셔츠",
        option_names=["블랙", "남성용"],
        detail_text="여름용 민소매 스웨터 티셔츠입니다"
    )

    print("\nFINAL RESULT\n", result)
