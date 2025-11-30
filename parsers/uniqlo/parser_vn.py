# parsers/uniqlo/parser_vn.py

from parsers.base_parser import BaseParser
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urlsplit, urlunsplit

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def replace_color_code(url, new_code):
    u = urlparse(url)
    qs = parse_qs(u.query)
    qs["colorDisplayCode"] = [new_code]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))


def remove_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


class UniqloVietnamParser(BaseParser):

    def __init__(self, rules):
        self.rules = rules
        print("[UniqloVietnamParser] 파서 초기화 완료")

    # ---------------------------------------------------------
    def parse(self, html: str, request_raw_html=None, original_url=None):
        print("[UniqloVietnamParser] parse 시작")

        soup = BeautifulSoup(html, "html.parser")

        # -------------------------------
        # 사이즈표 raw HTML
        # -------------------------------
        size_html_raw = self._parse_size_chart(soup)
        headers, rows = self.extract_raw_size_chart(size_html_raw)

        # -------------------------------
        # 색상 파싱
        # -------------------------------
        colors = self._parse_color_list(soup)

        # -------------------------------
        # 상세설명
        # -------------------------------
        detail_description = self._parse_detail_description(soup)

        # -------------------------------
        # 영상
        # -------------------------------
        video_url = self._parse_video(soup)

        # 임시 저장
        variants = {}

        seen = set()
        for c in colors:
            code = c["code"]
            if not code or code in seen:
                continue
            seen.add(code)

            variant_url = replace_color_code(original_url, code)
            html_variant = request_raw_html(variant_url, code)
            if not html_variant:
                continue

            variants[code] = self._parse_variant_detail(html_variant)

        # -------------------------------
        # 병합
        # -------------------------------
        merged_sizes = {}
        merged_sizes_order = []
        merged_prices = {}

        color_main_images = {}
        sub_images = []
        feature_images = []

        seen_sub = set()
        seen_feature = set()

        for code, variant in variants.items():

            merged_prices[code] = variant.get("price")

            for url in variant.get("images", []):
                lower = url.lower()

                if "/item/" in lower:
                    if code not in color_main_images:
                        color_main_images[code] = url
                    continue

                if "/sub/" in lower:
                    if url not in seen_sub:
                        seen_sub.add(url)
                        sub_images.append(url)
                    continue

                if "/feature/" in lower:
                    if url not in seen_feature:
                        seen_feature.add(url)
                        feature_images.append(url)
                    continue

            # 사이즈
            for s in variant.get("sizes", []):
                name = s["name"]
                if name not in merged_sizes:
                    merged_sizes[name] = {
                        "name": name,
                        "code": s.get("code"),
                        "disabled": s.get("disabled", False)
                    }
                    merged_sizes_order.append(name)
                else:
                    if merged_sizes[name]["code"] is None and s.get("code"):
                        merged_sizes[name]["code"] = s["code"]
                    if s.get("disabled", False):
                        merged_sizes[name]["disabled"] = True

        # -------------------------------
        final_images = sub_images + feature_images

        final_colors = [
            {
                "name": c["name"],
                "code": c["code"],
                "image": color_main_images.get(c["code"])
            }
            for c in colors
        ]

        option_groups = []

        if final_colors:
            option_groups.append({
                "group_name": "색상",
                "values": [
                    {
                        "name": col["name"],
                        "code": col["code"],
                        "image": col.get("image"),
                        "disabled": False
                    }
                    for col in final_colors
                ]
            })

        if merged_sizes_order:
            option_groups.append({
                "group_name": "사이즈",
                "values": [
                    {
                        "name": merged_sizes[name]["name"],
                        "code": merged_sizes[name].get("code"),
                        "disabled": merged_sizes[name].get("disabled", False)
                    }
                    for name in merged_sizes_order
                ]
            })

        # 최종 구조
        return {
            "colors": final_colors,
            "prices": merged_prices,
            "sizes": [merged_sizes[n] for n in merged_sizes_order],
            "images": final_images,
            "detail_description": detail_description,
            "size_html": size_html_raw,
            "options": option_groups,
            "video": video_url,
            "size_headers_original": headers,
            "size_rows_original": rows,
            "size_html_raw": size_html_raw
        }

    # ---------------------------------------------------------
    def _parse_color_list(self, soup):
        colors = []
        for css in self.rules["color"]:
            for btn in soup.select(css):
                img = btn.find("img")
                name = img.get("alt") if img and img.get("alt") else None
                code = btn.get("value")
                chip = img.get("src") if img else None

                if name and code:
                    colors.append({
                        "name": name.strip(),
                        "code": code,
                        "chip_image": chip
                    })
        return colors

    # ---------------------------------------------------------
    def _parse_variant_detail(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return {
            "price": self._parse_price(soup),
            "images": self._parse_images(soup),
            "sizes": self._parse_sizes(soup)
        }

    # ---------------------------------------------------------
    def _parse_price(self, soup):
        for css in self.rules["price"]:
            tag = soup.select_one(css)
            if tag:
                txt = tag.get_text(strip=True)
                if txt:
                    return txt
        return ""

    def _parse_video(self, soup):
        video = soup.find("video")
        if not video:
            return None
        url = video.get("data-src") or video.get("src")
        if url and url.startswith("http"):
            return url
        return None

    def _parse_images(self, soup):
        result = []

        for css in self.rules["image_main"]:
            for node in soup.select(css):
                url = node.get("src") or node.get("data-src")
                if url and url.startswith("http"):
                    clean = remove_query(url)
                    if clean.lower().endswith(IMAGE_EXT):
                        result.append(clean)

        for css in self.rules["image_feature"]:
            for node in soup.select(css):
                url = node.get("src")
                if url and url.startswith("http"):
                    clean = remove_query(url)
                    if clean.lower().endswith(IMAGE_EXT):
                        result.append(clean)

        return list(dict.fromkeys(result))

    # ---------------------------------------------------------
    def _parse_sizes(self, soup):
        sizes = []
        for css in self.rules["size"]:
            for btn in soup.select(css):
                name = btn.get_text(strip=True)
                code = btn.get("value")

                disabled = False
                soldout = self.rules.get("soldout")
                if soldout:
                    if btn.get(soldout["attribute"]) == soldout["value"]:
                        disabled = True

                if name:
                    sizes.append({
                        "name": name,
                        "code": code,
                        "disabled": disabled
                    })

        clean = []
        seen = set()
        for s in sizes:
            if s["name"] not in seen:
                seen.add(s["name"])
                clean.append(s)

        return clean

    # ---------------------------------------------------------
    def _parse_detail_description(self, soup):
        rules = self.rules.get("detail", {})

        def extract(sel):
            if not sel:
                return ""
            texts = []
            for node in soup.select(sel):
                t = node.get_text(" ", strip=True)
                if t:
                    texts.append(t)
            return " ".join(texts)

        parts = []
        if rules.get("features"):
            t = extract(rules["features"])
            if t:
                parts.append(t)
        if rules.get("spec"):
            t = extract(rules["spec"])
            if t:
                parts.append(t)
        if rules.get("material"):
            t = extract(rules["material"])
            if t:
                parts.append(t)

        return "\n\n".join(parts).strip()

    # ---------------------------------------------------------
    def _parse_size_chart(self, soup):
        table = soup.find("table", class_="size-chart")
        if table:
            return str(table)
        div = soup.find("div", class_="size-chart")
        if div:
            return str(div)
        wrapper = soup.find("div", {"data-testid": "size-chart"})
        if wrapper:
            return str(wrapper)
        fallback = soup.find("section", id="size-chart")
        if fallback:
            return str(fallback)
        return ""

    def extract_raw_size_chart(self, html):
        if not html:
            return [], []
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return [], []
        rows = [
            [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            for tr in table.find_all("tr")
        ]
        if len(rows) < 2:
            return [], []
        return rows[0], rows[1:]
