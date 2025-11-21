from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def replace_color_code(url, new_code):
    u = urlparse(url)
    qs = parse_qs(u.query)

    qs["colorDisplayCode"] = [new_code]

    new_query = urlencode(qs, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))
