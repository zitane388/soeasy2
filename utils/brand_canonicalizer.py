import json
import threading
from pathlib import Path

from utils.path import p
from llm.llm_product_name_generator import generate_canonical_brand_from_llm

_LOCK = threading.Lock()
_CACHE_PATH = Path(p("data", "brand_canonical_cache.json"))


def _normalize_key(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _build_cache_key(raw_brand: str) -> str:
    # versioned key to avoid stale values from previous normalization rules
    return f"v2|{_normalize_key(raw_brand)}"


def _load_cache() -> dict:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def canonicalize_brand(raw_brand: str, product_name: str = "") -> str:
    """
    1) local JSON cache match
    2) if miss, ask LLM
    3) save to cache
    """
    raw_brand = (raw_brand or "").strip()
    if not raw_brand:
        return ""

    key = _build_cache_key(raw_brand)
    if not key:
        return ""

    with _LOCK:
        cache = _load_cache()
        cached = cache.get(key)
        if isinstance(cached, str) and cached.strip():
            return cached.strip()

    llm_out = generate_canonical_brand_from_llm(
        raw_brand=raw_brand,
        product_name=product_name,
    )
    canonical = (llm_out or raw_brand).strip()

    with _LOCK:
        cache = _load_cache()
        cache[key] = canonical
        _save_cache(cache)

    return canonical
