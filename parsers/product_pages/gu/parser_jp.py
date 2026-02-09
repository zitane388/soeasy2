# parsers/gu/parser_jp.py
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urlsplit, urlunsplit
import re

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


class GUJapanParser:

    def __init__(self, rules, brand="GU"):
        self.rules = rules
        self.brand = brand

    def parse(self, scraper, original_url, first_html):

        soup = BeautifulSoup(first_html, "html.parser")
        
        model_number_global = self._extract_model_number_global(soup)

        # ---------------------------------------------------
        # 사이즈표 HTML
        # ---------------------------------------------------
        size_html_raw = self._parse_size_chart(soup)
        headers, rows = self.extract_raw_size_chart(size_html_raw)

        # ---------------------------------------------------
        # 색상 (chip_image 포함)
        # ---------------------------------------------------
        colors = self._parse_color_list(soup)

        # ---------------------------------------------------
        # 상세설명
        # ---------------------------------------------------
        detail_description = self._parse_detail_description(soup)

        # ---------------------------------------------------
        # 상품명 (original_name)
        # ---------------------------------------------------
        raw_name = self.extract_gu_name_soup(soup)

        # ---------------------------------------------------
        # 영상
        # ---------------------------------------------------
        video_url = self._parse_video(soup)

        # ---------------------------------------------------
        # 임시 구조
        # ---------------------------------------------------
        results = {
            "colors": colors,
            "variants": {},
            "detail_description": detail_description
        }

        seen = set()
        for c in colors:
            code = c["code"]
            if not code or code in seen:
                continue
            seen.add(code)

            variant_url = replace_color_code(original_url, code)
            html_variant = scraper.request_color_html(original_url, code)
            if not html_variant:
                continue

            results["variants"][code] = self._parse_variant_detail(html_variant)

        # ---------------------------------------------------
        # 병합 (사이즈 / 가격 / 이미지)
        # ---------------------------------------------------
        merged_sizes = {}
        merged_sizes_order = []
        merged_prices = {}

        color_main_images = {}
        sub_images = []
        feature_images = []
        seen_sub = set()
        seen_feature = set()

        for color_code in results["variants"].keys():
            variant = results["variants"][color_code]

            merged_prices[color_code] = variant.get("price", "")

            for url in variant.get("images", []):
                lower = url.lower()

                if "/item/" in lower or "/goods/" in lower:
                    if color_code not in color_main_images:
                        color_main_images[color_code] = url
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

            for s in variant.get("sizes", []):
                name = s.get("name")
                if not name:
                    continue

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

        final_images = sub_images + feature_images

        # ---------------------------------------------------
        # colors + image + chip_image
        # ---------------------------------------------------
        final_colors = []
        for c in colors:
            code = c["code"]
            final_colors.append({
                "name": c["name"],
                "code": code,
                "image": color_main_images.get(code),
                "chip_image": c.get("chip_image")
            })

        # ---------------------------------------------------
        # 옵션 그룹 (표준)
        # ---------------------------------------------------
        option_groups = []

        if final_colors:
            option_groups.append({
                "group_name": "색상",
                "values": [
                    {
                        "name": c["name"],
                        "code": c.get("code"),
                        "image": c.get("image"),
                        "chip_image": c.get("chip_image"),
                        "disabled": False
                    }
                    for c in final_colors
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

        detail_text = results["detail_description"]

        return {
            "original_name": raw_name,
            "colors": final_colors,
            "prices": merged_prices,
            "sizes": [merged_sizes[name] for name in merged_sizes_order],
            "images": final_images,
            "detail_description": detail_text,
            "model_number": model_number_global,
            "options": option_groups,
            "video": video_url,
            "size_headers_original": headers,
            "size_rows_original": rows,
            "size_html_raw": size_html_raw
        }
        
    
    def _extract_model_number_global(self, soup: BeautifulSoup):
        """
        페이지 전체 HTML 기준 상품번호 추출
        상세설명에 없어도 잡히도록 전역 탐색
        """
        import re

        text = soup.get_text(" ", strip=True)

        m = re.search(r"商品番号[:：]?\s*([0-9A-Za-z\-]+)", text)
        if m:
            return m.group(1)

        return None
        
        
    def extract_gu_name_soup(self, soup):
        main = soup.find("main")
        if not main:
            return None
        node = main.find("div", {"data-testid": "ITOTypography"})
        return node.get_text(strip=True) if node else None

    def _parse_color_list(self, soup):
        colors = []
        for css in self.rules["color"]:
            for btn in soup.select(css):
                img = btn.find("img")
                name = img.get("alt").strip() if img and img.get("alt") else None
                code = btn.get("value")
                chip = img.get("src") if img else None
                if code and name:
                    colors.append({
                        "name": name,
                        "code": code,
                        "chip_image": chip
                    })
        return colors

    def _parse_variant_detail(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return {
            "price": self._parse_price(soup),
            "images": self._parse_images(soup),
            "sizes": self._parse_sizes(soup)
        }

    def _parse_price(self, soup):
        for css in self.rules["price"]:
            node = soup.select_one(css)
            if node:
                return node.get_text(strip=True)
        return ""

    def _parse_video(self, soup):
        v = soup.find("video")
        if not v:
            return None
        url = v.get("data-src") or v.get("src")
        return url if url and url.startswith("http") else None

    def _parse_images(self, soup):
        images = []
        for css in self.rules["image_main"]:
            for img in soup.select(css):
                url = img.get("src") or img.get("data-src")
                if url and url.startswith("http"):
                    url = remove_query(url)
                    if url.lower().endswith(IMAGE_EXT):
                        images.append(url)
        for css in self.rules["image_feature"]:
            for img in soup.select(css):
                url = img.get("src")
                if url and url.startswith("http"):
                    images.append(remove_query(url))
        return list(dict.fromkeys(images))

    def _parse_sizes(self, soup):
        sizes = []
        for css in self.rules["size"]:
            for btn in soup.select(css):
                name = btn.get_text(strip=True)
                code = btn.get("value")
                disabled = False
                soldout = self.rules.get("soldout")
                if soldout and btn.get(soldout["attribute"]) == soldout["value"]:
                    disabled = True
                if name:
                    sizes.append({
                        "name": name,
                        "code": code,
                        "disabled": disabled
                    })
        seen = set()
        return [s for s in sizes if not (s["name"] in seen or seen.add(s["name"]))]

    def _parse_detail_description(self, soup):
        rules = self.rules.get("detail", {})
        texts = []
        for key in ("features", "spec", "material"):
            for sel in rules.get(key, []):
                for n in soup.select(sel):
                    t = n.get_text(" ", strip=True)
                    if t:
                        texts.append(t)
        text = "\n\n".join(texts).strip()
        
        # 商品番号 / 品番 라벨 + 값 전체 제거
        text = re.sub(r"商品番号\s*[:：]?\s*[0-9A-Za-z\-]*", "", text)
        text = re.sub(r"品番\s*[:：]?\s*[0-9A-Za-z\-]*", "", text)

        # 단독 숫자 상품코드 줄 제거
        lines = text.split("\n")
        lines = [l for l in lines if not re.fullmatch(r"\s*\d{6,8}\s*", l)]
        text = "\n".join(lines)

        # 상품번호 제거 후 생긴 ' : ' 단독 구문만 정리
        text = re.sub(r"\n\s*[:：]\s*\n", "\n", text)

        # 공백 정리
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ ]{2,}", " ", text).strip()
        
        return text

    def _parse_size_chart(self, soup: BeautifulSoup):
        # 1) class="size-chart" table
        table = soup.find("table", class_="size-chart")
        if table:
            return str(table)

        # 2) class="size-chart" div
        div = soup.find("div", class_="size-chart")
        if div:
            return str(div)

        # 3) data-testid="size-chart" wrapper
        wrapper = soup.find("div", attrs={"data-testid": "size-chart"})
        if wrapper:
            return str(wrapper)

        # 4) section id="size-chart"
        sec = soup.find("section", id="size-chart")
        if sec:
            return str(sec)

        # 5) 마지막 fallback: 헤더 행(tr.size-chart-row--heading)이 있으면 그 상위 컨테이너 반환
        heading_tr = soup.select_one("tr.size-chart-row--heading")
        if heading_tr:
            # table이 있으면 table, 없으면 가까운 div/section까지
            parent_table = heading_tr.find_parent("table")
            if parent_table:
                return str(parent_table)
            parent_div = heading_tr.find_parent(["div", "section"])
            if parent_div:
                return str(parent_div)

        return ""


    def extract_raw_size_chart(self, html: str):
        if not html:
            return [], []

        soup = BeautifulSoup(html, "html.parser")

        # 1) table 기반
        table = soup.find("table")
        if table:
            rows = []
            for tr in table.find_all("tr"):
                cols = tr.find_all(["th", "td"])
                cells = [c.get_text(strip=True) for c in cols]
                if cells:
                    rows.append(cells)

            if len(rows) >= 2:
                return rows[0], rows[1:]
            return [], []

        # 2) table이 없을 때: GU/Uniqlo ITO 구조(네가 올린 tr 클래스) 직접 처리
        trs = soup.select("tr.size-chart-row")
        if not trs:
            return [], []

        rows = []
        for tr in trs:
            cols = tr.find_all(["th", "td"])
            cells = [c.get_text(strip=True) for c in cols]
            if cells:
                rows.append(cells)

        if len(rows) >= 2:
            return rows[0], rows[1:]

        return [], []
