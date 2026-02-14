import re
import traceback

from llm.llm_product_name_generator import (
    generate_product_name_from_llm,
    generate_product_name_from_llm_with_image,
)

MAX_LLM_INPUT_LEN = 80
MAX_FINAL_NAME_LEN = 40
MODEL_PATTERN = re.compile(r"\b[A-Z0-9]{2,}-[A-Z0-9]{2,}\b")
LIKELY_ITEM_ID_PATTERN = re.compile(r"^[A-Z]-\d{8,}$")


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s{2,}", " ", (text or "")).strip()


def normalize_gender_keywords(name: str) -> str:
    if not name:
        return name

    text = str(name)

    for p in [r"\bunisex\b", r"남녀공용", r"남여공용", r"유니섹스"]:
        text = re.sub(p, "", text, flags=re.IGNORECASE)

    for p in [r"\bmen\b", r"\bmens\b", r"맨즈", r"남성용", r"남자"]:
        text = re.sub(p, "남성", text, flags=re.IGNORECASE)

    for p in [r"\bwomen\b", r"\bwomens\b", r"우먼", r"여성용", r"여자"]:
        text = re.sub(p, "여성", text, flags=re.IGNORECASE)

    return _normalize_spaces(text)


def _compact_name_for_llm(name: str, max_len: int = MAX_LLM_INPUT_LEN) -> str:
    text = _normalize_spaces(name)
    if not text:
        return ""

    text = re.sub(r"\(([^)]{1,24})\)", r" \1 ", text)
    text = re.sub(r"\[[^\]]{1,24}\]", " ", text)

    for p in [r"정품", r"국내배송", r"당일출고", r"할인", r"특가", r"무료배송"]:
        text = re.sub(p, " ", text, flags=re.IGNORECASE)

    text = _normalize_spaces(text)

    model = None
    m = MODEL_PATTERN.search(text)
    if m:
        model = m.group(0)

    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0].strip() or text[:max_len].strip()

    if model and model.lower() not in text.lower():
        text = f"{text} {model}".strip()

    return _normalize_spaces(text)


def _dedupe_tokens(text: str) -> str:
    tokens = _normalize_spaces(text).split(" ")
    out = []
    seen = set()
    for t in tokens:
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t)
    return " ".join(out)


def _drop_redundant_tokens(text: str) -> str:
    """
    Generic redundancy cleanup without domain-specific keyword rules.
    - keeps first occurrence order
    - drops later token if it is a strict substring of an already kept token
    """
    tokens = _normalize_spaces(text).split(" ")
    kept = []
    kept_lower = []

    for token in tokens:
        t = token.strip()
        if not t:
            continue

        tl = t.lower()
        if tl in kept_lower:
            continue

        # generic overlap rule (not category-specific)
        if any(tl in k for k in kept_lower if tl != k):
            continue

        kept.append(t)
        kept_lower.append(tl)

    return " ".join(kept)


def _trim_to_limit_keep_tail_model(text: str, max_len: int = MAX_FINAL_NAME_LEN) -> str:
    text = _normalize_spaces(text)
    if len(text) <= max_len:
        return text

    model = None
    matches = MODEL_PATTERN.findall(text)
    if matches:
        # Keep only one model token at tail (prefer first occurrence).
        model = matches[0]
        text = MODEL_PATTERN.sub("", text)
        text = _normalize_spaces(text)

    if model:
        budget = max_len - len(model) - 1
        if budget < 10:
            return model
        head = text[:budget].rsplit(" ", 1)[0].strip() or text[:budget].strip()
        return _normalize_spaces(f"{head} {model}")

    return text[:max_len].rsplit(" ", 1)[0].strip() or text[:max_len].strip()


def _has_any_model_token(text: str) -> bool:
    return bool(MODEL_PATTERN.search(text or ""))


def _is_appendable_model_token(model_no: str | None) -> bool:
    if not model_no:
        return False
    m = str(model_no).strip()
    if not m:
        return False
    # Avoid appending site-level product IDs like A-10893435601 as model.
    if LIKELY_ITEM_ID_PATTERN.fullmatch(m):
        return False
    return True


def _fallback_name_without_llm(translated_name: str, model_no: str | None) -> str:
    out = _compact_name_for_llm(translated_name, max_len=60)
    out = normalize_gender_keywords(out)
    out = _dedupe_tokens(out)
    out = _drop_redundant_tokens(out)

    # Append model only if there is no model-like token at all.
    if _is_appendable_model_token(model_no) and not _has_any_model_token(out):
        m = str(model_no).strip()
        if m:
            out = f"{out} {m}".strip()

    out = _trim_to_limit_keep_tail_model(out, MAX_FINAL_NAME_LEN)
    return _normalize_spaces(out)


def _post_process_final_name(result: str, model_no: str | None) -> str:
    out = normalize_gender_keywords(result)
    out = _dedupe_tokens(out)
    out = _drop_redundant_tokens(out)

    # Do not append model_no if result already contains another model token.
    if _is_appendable_model_token(model_no) and not _has_any_model_token(out):
        m = str(model_no).strip()
        if m:
            out = f"{out} {m}".strip()

    out = _trim_to_limit_keep_tail_model(out, MAX_FINAL_NAME_LEN)
    return _normalize_spaces(out)


def generate_final_name(
    product_item,
    translated_name: str,
    keyword_list: list[str],
    image_url: str = None,
) -> str:
    print("\n================ [NAME GENERATOR START] ================")
    print("translated_name =", translated_name)
    print("keyword_list =", keyword_list)
    print("image_url =", image_url)
    print("product_item.model_number =", getattr(product_item, "model_number", None))

    try:
        if not translated_name:
            print("[SKIP] translated_name is empty")
            return ""

        model_no = getattr(product_item, "model_number", None)
        keywords = keyword_list or []
        llm_input_name = translated_name

        if not keywords:
            print("[FALLBACK] keyword extraction failed -> try LLM with compact name")
            llm_input_name = _compact_name_for_llm(translated_name, max_len=MAX_LLM_INPUT_LEN)
            print("llm_input_name =", llm_input_name)

        if image_url and isinstance(image_url, str) and image_url.startswith("http"):
            result = generate_product_name_from_llm_with_image(
                product_name=llm_input_name,
                keywords=keywords,
                image_url=image_url,
            )
        else:
            result = generate_product_name_from_llm(
                product_name=llm_input_name,
                keywords=keywords,
            )

        if not result:
            print("[WARN] LLM returned empty; apply deterministic fallback")
            return _fallback_name_without_llm(translated_name, model_no)

        result = _post_process_final_name(result, model_no)
        print("[FINAL RESULT RETURN] =", result)
        print("================ [NAME GENERATOR END] ================\n")
        return result

    except Exception:
        print("[NAME GENERATOR ERROR]")
        traceback.print_exc()
        print("[FALLBACK] return deterministic cleaned name")
        return _fallback_name_without_llm(
            translated_name,
            getattr(product_item, "model_number", None),
        )
