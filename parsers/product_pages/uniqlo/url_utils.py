from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def replace_color_code(url, new_code):
    """
    colorDisplayCode / color / colorCode 형태 모두 지원
    (기존 메소드명 그대로 유지)
    """

    u = urlparse(url)
    qs = parse_qs(u.query)

    # 유니클로 사이트별 색상 파라미터 차이 자동 대응
    replaced = False
    for key in ["colorDisplayCode", "color", "colorCode"]:
        if key in qs:
            qs[key] = [new_code]
            replaced = True

    # 기존 쿼리에 색상 파라미터가 없는 경우 기본 colorDisplayCode 추가
    if not replaced:
        qs["colorDisplayCode"] = [new_code]

    new_query = urlencode(qs, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))


def replace_size_code(url, new_code):
    """
    sizeCode / size / sizeCode 형태 지원
    measurementUnit=cm 자동 보장
    """

    u = urlparse(url)
    qs = parse_qs(u.query)

    replaced = False
    for key in ["sizeCode", "size"]:
        if key in qs:
            qs[key] = [new_code]
            replaced = True

    if not replaced:
        qs["sizeCode"] = [new_code]

    # 사이즈표는 항상 cm 기준
    qs["measurementUnit"] = ["cm"]

    new_query = urlencode(qs, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))
