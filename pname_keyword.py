import re
import urllib.parse

import requests
from bs4 import BeautifulSoup, Tag

MAX_SEARCH_QUERY_LEN = 55
MAX_KEYWORDS = 50
MIN_BRACKET_BLOCKS_FOR_COMPACT = 2
MIN_SEPARATORS_FOR_COMPACT = 3
MIN_NOISE_HITS_FOR_COMPACT = 2
NOISE_PATTERNS = [
    r"정품",
    r"특가",
    r"할인",
    r"무료배송",
    r"당일출고",
    r"국내배송",
]


def clean_and_split(text):
    words = re.findall(r"[\uac00-\ud7a3a-zA-Z0-9]+", text or "")
    filtered = []
    for w in words:
        if re.fullmatch(r"[a-zA-Z]+", w):
            continue
        if re.fullmatch(r"[0-9]+", w):
            continue
        filtered.append(w)
    return filtered


def has_korean(text: str) -> bool:
    return bool(re.search(r"[\uac00-\ud7a3]", text or ""))


def _normalize_token(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").strip()).lower()


def _post_filter_keywords(query: str, keywords: list[str]) -> list[str]:
    """
    Generic quality filter:
    - remove too-long merged tokens
    - keep tokens that overlap with query terms
    """
    if not keywords:
        return []

    query_terms = clean_and_split(query)
    query_norm = {_normalize_token(t) for t in query_terms if t}
    out = []
    seen = set()
    soft_candidates = []

    for kw in keywords:
        k = (kw or "").strip()
        if not k:
            continue
        kn = _normalize_token(k)
        if not kn or kn in seen:
            continue

        # Drop only obvious merged noise (too long + no separator).
        if len(k) > 14 and (" " not in k):
            continue

        # Keep if token itself is in query terms
        if kn in query_norm:
            seen.add(kn)
            out.append(k)
            continue

        # Keep if any query term is contained.
        if any(q and q in kn for q in query_norm):
            if len(k) <= 14:
                seen.add(kn)
                out.append(k)
                continue

        # Soft keep: short Korean keyword can still be useful for LLM naming.
        if has_korean(k) and len(k) <= 8:
            soft_candidates.append((kn, k))

    # Append soft candidates up to limit
    for kn, k in soft_candidates:
        if kn in seen:
            continue
        seen.add(kn)
        out.append(k)

    # keep enough signal keywords, not too many noisy ones
    return out[:MAX_KEYWORDS]


def _compact_search_query(product_name: str, brand: str, max_len: int = MAX_SEARCH_QUERY_LEN) -> str:
    text = re.sub(r"\s+", " ", (product_name or "")).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text

    model = None
    m = re.search(r"\b[A-Z0-9]{2,}-[A-Z0-9]{2,}\b", text)
    if m:
        model = m.group(0)

    short = text[:max_len].rsplit(" ", 1)[0].strip()
    if not short:
        short = text[:max_len].strip()

    if brand and brand.lower() not in short.lower():
        short = f"{brand} {short}".strip()

    if model and model.lower() not in short.lower():
        short = f"{short} {model}".strip()

    return re.sub(r"\s{2,}", " ", short).strip()


def _compact_search_query_llm(product_name: str, brand: str, max_len: int = MAX_SEARCH_QUERY_LEN) -> str:
    """
    LLM compact-query path. Lazy import to avoid hard dependency during startup.
    """
    try:
        from llm.llm_product_name_generator import generate_compact_search_query_from_llm
    except Exception as e:
        print("[KEYWORD_EXTRACT][LLM_COMPACT][SKIP] import failed:", repr(e))
        return ""

    try:
        out = generate_compact_search_query_from_llm(
            product_name=product_name,
            brand=brand,
            max_len=max_len,
        )
        out = re.sub(r"\s{2,}", " ", (out or "").strip())
        if not out:
            return ""

        # Keep model token if original had one and output lost it.
        model = None
        m = re.search(r"\b[A-Z0-9]{2,}-[A-Z0-9]{2,}\b", product_name or "")
        if m:
            model = m.group(0)
        if model and model.lower() not in out.lower():
            out = f"{out} {model}".strip()

        # Hard bound for safety after post-fixes.
        if len(out) > max_len:
            out = out[:max_len].rsplit(" ", 1)[0].strip() or out[:max_len].strip()
        return out
    except Exception as e:
        print("[KEYWORD_EXTRACT][LLM_COMPACT][ERROR]", repr(e))
        return ""


def _should_retry_with_compact(product_name: str) -> tuple[bool, str]:
    text = re.sub(r"\s+", " ", (product_name or "")).strip()
    if not text:
        return False, "empty"

    if len(text) > MAX_SEARCH_QUERY_LEN:
        return True, f"len>{MAX_SEARCH_QUERY_LEN}"

    bracket_blocks = len(re.findall(r"\([^)]*\)|\[[^\]]*\]", text))
    if bracket_blocks >= MIN_BRACKET_BLOCKS_FOR_COMPACT:
        return True, f"brackets>={MIN_BRACKET_BLOCKS_FOR_COMPACT}"

    separators = len(re.findall(r"[/|,]", text))
    if separators >= MIN_SEPARATORS_FOR_COMPACT:
        return True, f"separators>={MIN_SEPARATORS_FOR_COMPACT}"

    noise_hits = 0
    for p in NOISE_PATTERNS:
        if re.search(p, text, flags=re.IGNORECASE):
            noise_hits += 1
    if noise_hits >= MIN_NOISE_HITS_FOR_COMPACT:
        return True, f"noise>={MIN_NOISE_HITS_FOR_COMPACT}"

    return False, "not_triggered"


def _extract_keywords_once(query: str, brand: str, require_brand_match: bool = True) -> list[str]:
    query = (query or "").strip()
    brand_l = (brand or "").strip().lower()
    if not query:
        return []
    if require_brand_match and not brand_l:
        return []

    url = f"https://search.naver.com/search.naver?where=nexearch&query={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
    }

    print("[KEYWORD_EXTRACT] requests.get START", "| query=", query)
    resp = requests.get(url, headers=headers, timeout=5)
    print(
        "[KEYWORD_EXTRACT] requests.get DONE",
        f"status={resp.status_code}",
        f"len={len(resp.text) if resp.text else 0}",
    )

    if resp.status_code != 200 or not resp.text:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    keywords = set()

    class_groups = ["_1RbzoNnJ", "dVWEbQ7N"]
    for cls in class_groups:
        for ul in soup.find_all("ul", class_=cls):
            for li in ul.find_all("li"):
                li_words = []

                for span in li.find_all("span"):
                    if span.find("mark"):
                        for child in span.children:
                            text = child.get_text(strip=True) if isinstance(child, Tag) else str(child)
                            li_words.extend(clean_and_split(text))

                for a in li.find_all("a"):
                    for span in a.find_all("span"):
                        if not span.get("class"):
                            li_words.extend(clean_and_split(span.get_text(strip=True)))

                li_words = [w for w in li_words if has_korean(w)]
                if (not require_brand_match) or any(brand_l in w.lower() for w in li_words):
                    keywords.update(li_words)

    for ul in soup.find_all("ul", class_="KoFfoLbL"):
        for li in ul.find_all("li"):
            li_words = []
            for span in li.find_all("span"):
                if not span.get("class"):
                    li_words.extend(clean_and_split(span.get_text(strip=True)))

            li_words = [w for w in li_words if has_korean(w)]
            if (not require_brand_match) or any(brand_l in w.lower() for w in li_words):
                keywords.update(li_words)

    return sorted(_post_filter_keywords(query, list(keywords)))


def extract_keywords(product_name: str, brand: str) -> list:
    print(
        f"[KEYWORD_EXTRACT][INPUT] product_name='{product_name}' | "
        f"brand='{brand}' | has_korean={has_korean(product_name) if product_name else False}"
    )

    if not product_name:
        print("[KEYWORD_EXTRACT][SKIP] product_name missing")
        return []

    try:
        compact = ""
        llm_compact = ""

        # 1) Always try original query first.
        result = _extract_keywords_once(product_name, brand, require_brand_match=True)
        if result:
            print(
                f"[KEYWORD_EXTRACT][RESULT] query=original | count={len(result)} | keywords={result}"
            )
            return result

        # 2) Retry with compact query when initial criteria are triggered.
        should_retry, reason = _should_retry_with_compact(product_name)
        if should_retry:
            compact = _compact_search_query(product_name, brand, MAX_SEARCH_QUERY_LEN)
            if compact and compact != product_name:
                print(
                    "[KEYWORD_EXTRACT][RETRY] compact query enabled "
                    f"(reason={reason})"
                )
                result = _extract_keywords_once(compact, brand, require_brand_match=True)
                if result:
                    print(
                        f"[KEYWORD_EXTRACT][RESULT] query=compact | count={len(result)} | keywords={result}"
                    )
                    return result

            # 3) If deterministic compact also failed, try LLM compact query once.
            llm_compact = _compact_search_query_llm(product_name, brand, MAX_SEARCH_QUERY_LEN)
            if llm_compact and llm_compact not in (product_name, compact):
                print(
                    "[KEYWORD_EXTRACT][RETRY] llm compact query enabled "
                    f"(reason={reason}) | query={llm_compact}"
                )
                result = _extract_keywords_once(llm_compact, brand, require_brand_match=True)
                if result:
                    print(
                        f"[KEYWORD_EXTRACT][RESULT] query=llm_compact | count={len(result)} | keywords={result}"
                    )
                    return result

        # 4) Relaxed mode:
        # If strict brand matching keeps returning 0, retry once without brand constraint.
        # This covers marketplace brands (e.g., shop domain != product brand).
        for q in [product_name, compact, llm_compact]:
            if not q:
                continue
            result = _extract_keywords_once(q, brand, require_brand_match=False)
            if result:
                print(
                    f"[KEYWORD_EXTRACT][RESULT] query=relaxed | count={len(result)} | keywords={result}"
                )
                return result

        print("[KEYWORD_EXTRACT][RESULT] count=0")
        return []

    except Exception as e:
        print("[KEYWORD_EXTRACT][CRASH]", repr(e))
        return []
