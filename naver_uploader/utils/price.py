def parse_price(raw):
    if raw is None:
        return 0
    if isinstance(raw, int):
        return raw
    if not isinstance(raw, str):
        return 0

    return int(
        raw.replace("¥", "")
           .replace("₫", "")
           .replace(",", "")
           .replace(".", "")
           .strip()
    )
