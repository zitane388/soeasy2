import requests

# ==========================================
# 국가 → 기본 통화
# ==========================================
COUNTRY_CURRENCY_MAP = {
    "jp": "JPY",
    "kr": "KRW",
    "us": "USD",
    "eu": "EUR",
    "uk": "GBP",
    "cn": "CNY",
    "tw": "TWD",
    "hk": "HKD",
    "vn": "VND",   # ✅ 베트남 추가 (중요)
}

# ==========================================
# 환율 캐시
# ==========================================
_cached_rate = {}

def get_rate(currency: str) -> float:
    if not currency or currency == "KRW":
        return 1.0

    if currency in _cached_rate:
        return _cached_rate[currency]

    try:
        url = f"https://open.er-api.com/v6/latest/{currency}"
        r = requests.get(url, timeout=5).json()
        rate = r["rates"]["KRW"]
        _cached_rate[currency] = rate
        return rate
    except:
        fallback = {
            "JPY": 9.2,
            "USD": 1350,
            "EUR": 1480,
            "GBP": 1700,
            "CNY": 185,
            "VND": 0.055
        }.get(currency, 1000)

        _cached_rate[currency] = fallback
        return fallback


# ==========================================
# 🔥 가격 정규화 (여기가 핵심)
# ==========================================
def _to_int(v):
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        digits = "".join(c for c in v if c.isdigit())
        return int(digits) if digits else None
    return None


def _convert_to_krw(value, currency):
    if not value or not currency or currency == "KRW":
        return value, "KRW"

    num = _to_int(value)
    if not num:
        return value, currency

    krw = int(num * get_rate(currency))
    krw = ((krw + 9) // 10) * 10
    return krw, "KRW"


def normalize_price_to_krw(parsed: dict, country: str = None) -> dict:
    """
    parsed 결과물에서
    - price
    - prices
    를 모두 안전하게 KRW로 변환
    """

    default_currency = COUNTRY_CURRENCY_MAP.get(
        (country or "").lower()
    )

    # ----------------------------
    # 단일 price
    # ----------------------------
    price = parsed.get("price")
    if isinstance(price, dict):
        v, c = _convert_to_krw(
            price.get("value"),
            price.get("currency") or default_currency
        )
        price["value"] = v
        price["currency"] = c

    # ----------------------------
    # 컬러별 prices
    # ----------------------------
    prices = parsed.get("prices")
    if isinstance(prices, dict):
        for _, p in prices.items():
            if not isinstance(p, dict):
                continue

            v, c = _convert_to_krw(
                p.get("value"),
                p.get("currency") or default_currency
            )
            p["value"] = v
            p["currency"] = c

    return parsed
