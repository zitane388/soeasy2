# parsers/gu/parser_jp.py
from parsers.base_parser import BaseParser
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlsplit, urlunsplit
from utils.detail_description_generator import normalize_size_chart
import os

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def remove_query(url: str) -> str:
    """URL의 query 파라미터 제거"""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


class GUJapanParser(BaseParser):

    def __init__(self, rules):
        self.rules = rules
        print("[GUJapanParser] 파서 초기화 완료")

    # ============================================================
    # 메인 파서
    # ============================================================
    def parse(self, html: str, request_raw_html=None, original_url=None):
        print("[GUJapanParser] parse 시작")

        soup = BeautifulSoup(html, "html.parser")

        # ---------------------------------------------------------
        # 사이즈표 파싱
        # ---------------------------------------------------------
        size_html_raw = self._parse_size_chart(soup)
        headers, rows = self.extract_raw_size_chart(size_html_raw)

        # ---------------------------------------------------------
        # 색상 목록 파싱
        # ---------------------------------------------------------
        colors = self._parse_color_list(soup)
        print("[GUJapanParser] colors =", colors)

        # ---------------------------------------------------------
        # 상세설명
        # ---------------------------------------------------------
        detail_description = self._parse_detail_description(soup)

        # ---------------------------------------------------------
        # 영상 URL
        # ---------------------------------------------------------
        video_url = self._parse_video(soup)

        temp_results = {
            "colors": colors,
            "variants": {},
            "detail_description": detail_description
        }

        # ---------------------------------------------------------
        # 색상별 상세 페이지 로딩
        # ---------------------------------------------------------
        print(f"[GUJapanParser] 색상 루프 시작 ({len(colors)}개)")

        pid = self._extract_product_id(original_url)

        seen_codes = set()

        for c in colors:
            code = c["code"]
            name = c["name"]

            if not code or code in seen_codes:
                continue
            seen_codes.add(code)

            url_tpl = self.rules.get("color_url_template")
            if url_tpl and pid:
                variant_url = url_tpl.replace("{product_id}", pid).replace("{color_code}", code)
            else:
                variant_url = original_url  # fallback

            print(f"[GUJapanParser] 색상 '{name}' 요청 → {variant_url}")

            html_variant = request_raw_html(variant_url, code)
            if not html_variant:
                print(f"[GUJapanParser] {name} HTML 실패")
                continue

            temp_results["variants"][code] = self._parse_variant_detail(html_variant)

        # ---------------------------------------------------------
        # 병합 (가격 / 사이즈 / 이미지)
        # ---------------------------------------------------------
        merged_sizes = {}
        merged_sizes_order = []
        merged_prices = {}

        color_main_images = {}
        sub_images = []
        feature_images = []

        seen_sub = set()
        seen_feature = set()

        for code in temp_results["variants"].keys():
            variant = temp_results["variants"][code]

            # price
            merged_prices[code] = variant.get("price")

            # 이미지
            for url in variant.get("images", []):
                lower = url.lower()

                # 대표 이미지
                if "/item/" in lower or "/goods/" in lower:
                    if code not in color_main_images:
                        color_main_images[code] = url
                    continue

                # sub 이미지
                if "/sub/" in lower or "subimg" in lower:
                    if url not in seen_sub:
                        seen_sub.add(url)
                        sub_images.append(url)
                    continue

                # feature 이미지
                if "/feature/" in lower:
                    if url not in seen_feature:
                        seen_feature.add(url)
                        feature_images.append(url)
                    continue

            # 사이즈 병합
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

        # ---------------------------------------------------------
        # 최종 이미지
        # ---------------------------------------------------------
        final_images = sub_images + feature_images

        # ---------------------------------------------------------
        # colors + 대표이미지 묶기
        # ---------------------------------------------------------
        final_colors = []
        for c in colors:
            final_colors.append({
                "name": c["name"],
                "code": c["code"],
                "image": color_main_images.get(c["code"])
            })

        # ---------------------------------------------------------
        # 표준 옵션 그룹
        # ---------------------------------------------------------
        option_groups = []

        if final_colors:
            option_groups.append({
                "group_name": "색상",
                "values": [
                    {
                        "name": col["name"],
                        "code": col.get("code"),
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

        # ---------------------------------------------------------
        # 최종 결과 리턴
        # ---------------------------------------------------------
        return {
            "colors": final_colors,
            "prices": merged_prices,
            "sizes": [merged_sizes[n] for n in merged_sizes_order],
            "images": final_images,
            "detail_description": temp_results["detail_description"],
            "size_html": size_html_raw,
            "options": option_groups,
            "video": video_url,
            "size_headers_original": headers,
            "size_rows_original": rows,
            "size_html_raw": size_html_raw
        }

    # ============================================================
    # 1) 색상 목록 파싱
    # ============================================================
    def _parse_color_list(self, soup):
        colors = []

        for btn in soup.select("button[data-testid='ITOChip']"):

            # 사이즈 chip은 제외
            if btn.find_parent("div", class_="size-chip-group"):
                continue

            code = btn.get("value")
            name = None

            img = btn.select_one("img")
            if img:
                name = img.get("alt")
            else:
                name = btn.get_text(strip=True)

            if not code or not name:
                continue

            colors.append({
                "name": name,
                "code": code
            })

        return colors


    # ============================================================
    # 2) 색상별 상세 파싱
    # ============================================================
    def _parse_variant_detail(self, html):
        soup = BeautifulSoup(html, "html.parser")

        return {
            "price": self.extract_price(soup),
            "images": self._parse_images(soup),
            "sizes": self._parse_sizes(soup)
        }

    # ============================================================
    # 가격 파싱
    # ============================================================
    def extract_price(self, soup):
        selectors = self.rules.get("price", [])
        for sel in selectors:
            tag = soup.select_one(sel)
            if tag:
                return self.clean_text(tag.get_text())
        return None

    # ============================================================
    # 영상 파싱
    # ============================================================
    def _parse_video(self, soup):
        vid = soup.find("video")
        if not vid:
            return None

        url = vid.get("data-src") or vid.get("src")
        if not url or not url.startswith("http"):
            return None

        return url

    # ============================================================
    # 이미지 파싱 (video 포함)
    # ============================================================
    def _parse_images(self, soup):
        images = []

        for css in self.rules["image_main"]:
            for node in soup.select(css):
                url = None

                # 이미지 노드
                if node.name == "img":
                    url = node.get("src") or node.get("data-src")

                # 동영상 노드
                elif node.name == "video":
                    url = node.get("data-src") or node.get("src")

                if url and url.startswith("http"):
                    clean = remove_query(url)
                    images.append(clean)

        # feature 이미지
        for css in self.rules["image_feature"]:
            for img in soup.select(css):
                url = img.get("src")
                if url and url.startswith("http"):
                    images.append(remove_query(url))

        return list(dict.fromkeys(images))

    # ============================================================
    # 사이즈 파싱
    # ============================================================
    def _parse_sizes(self, soup):
        sizes = []

        for btn in soup.select("div.size-chip-group button[data-testid='ITOChip']"):
            name = btn.get_text(strip=True)
            code = btn.get("value")

            disabled = False

            soldout_rule = self.rules.get("soldout")
            if soldout_rule:
                if btn.get(soldout_rule["attribute"]) == soldout_rule["value"]:
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

    # ============================================================
    # 상세설명 파싱
    # ============================================================
    def _parse_detail_description(self, soup):
        rules = self.rules.get("detail", {})

        def collect(selector_list):
            texts = []
            if not selector_list:
                return ""
            for sel in selector_list:
                for n in soup.select(sel):
                    t = n.get_text(" ", strip=True)
                    if t:
                        texts.append(t)
            return " ".join(texts)

        parts = []

        if rules.get("features"):
            t = collect(rules["features"])
            if t:
                parts.append(t)

        if rules.get("spec"):
            t = collect(rules["spec"])
            if t:
                parts.append(t)

        if rules.get("material"):
            t = collect(rules["material"])
            if t:
                parts.append(t)

        return "\n\n".join(parts).strip()

    # ============================================================
    # 사이즈표 Raw HTML
    # ============================================================
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

    def extract_raw_size_chart(self, html: str):
        if not html:
            return [], []

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return [], []

        rows = []
        for tr in table.find_all("tr"):
            cols = tr.find_all(["th", "td"])
            row = [c.get_text(strip=True) for c in cols]
            rows.append(row)

        if len(rows) < 2:
            return [], []

        return rows[0], rows[1:]

    # ============================================================
    # Product ID 추출 (color_url_template 용)
    # ============================================================
    def _extract_product_id(self, url):
        try:
            parsed = urlparse(url)
            parts = parsed.path.split("/")
            for p in parts:
                if p.startswith("E") and "-" in p:
                    return p
        except:
            pass
        return None
