COUNTRY_CURRENCY_MAP = {
    "jp": "JPY",
    "kr": "KRW",
    "us": "USD",
    "eu": "EUR",
    "uk": "GBP",
    "cn": "CNY",
    "tw": "TWD",
    "hk": "HKD",
}

import requests

_cached_rate = {}

def get_rate(currency):
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
            "CNY": 185
        }.get(currency, 1000)

        _cached_rate[currency] = fallback
        return fallback
