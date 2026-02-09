from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urlsplit, urlunsplit
import re

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def remove_query(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, '', ''))


def build_size_url(product_code, size_code):
    return (
        f"https://www.uniqlo.com/vn/en/products/{product_code}/size"
        f"?sizeCode={size_code}&measurementUnit=cm"
    )


class UniqloVietnamParser:

    def __init__(self, rules, brand=None):
        self.rules = rules
        self.brand = brand

    # ------------------------------------------------------
    def parse(self, scraper, original_url, first_html):
    
        print("[VN_PARSER] parse() start")
        print("[VN_PARSER] original_url =", original_url)

        # ✅ 0) product_code 추출 (사이즈 차트용 핵심)
        try:
            product_code = original_url.split("/products/")[1].split("?")[0]
        except Exception as e:
            print("[VN_PARSER][ERROR] product_code extract failed:", e)
            product_code = None

        soup = BeautifulSoup(first_html, "html.parser")
        
        model_number_global = self._extract_model_number_global(soup)

        # ---------------------------------------------------
        # 1) 색상 / 상세 / 상품명 / 영상
        # ---------------------------------------------------
        colors = self._parse_color_list(soup)

        detail_description = self._parse_detail_description(soup)
        raw_name = self.extract_uniqlo_name_soup(soup)
        video_url = self._parse_video(soup)
        results = {
            "colors": colors,
            "variants": {},
            "detail_description": detail_description
        }

        # ---------------------------------------------------
        # 2) 색상별 variant 수집
        # ---------------------------------------------------
        seen = set()
        for c in colors:
            code = c.get("code")
            if not code or code in seen:
                continue
            seen.add(code)

            html_variant = scraper.request_color_html(original_url, code)

            if not html_variant:
                continue

            results["variants"][code] = self._parse_variant_detail(html_variant)


        # ---------------------------------------------------
        # 3) variants 병합
        # ---------------------------------------------------
        merged_sizes = {}
        merged_sizes_order = []
        merged_prices = {}

        color_main_images = {}
        sub_images = []
        feature_images = []
        seen_sub = set()
        seen_feature = set()

        for color_code, variant in results["variants"].items():
            merged_prices[color_code] = variant.get("price", "")

            for url in variant.get("images", []):
                lower = url.lower()

                if "/item/" in lower:
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
                        
                        
                        

        # ---------------------------------------------------
        # 4) 사이즈 차트 수집
        #    - ONE SIZE 단일인 경우 스킵
        # ---------------------------------------------------
        def _is_one_size_only(size_names):
            if len(size_names) != 1:
                return False

            name = size_names[0].strip().upper()
            return name in {
                "ONE SIZE",
                "ONESIZE",
                "FREE",
                "FREE SIZE"
            }


        if product_code and merged_sizes_order:
            # 🔥 ONE SIZE 단일이면 사이즈표 요청 안 함
            if _is_one_size_only(merged_sizes_order):
                size_html_raw = ""
                headers, rows = [], []
                print("[VN_PARSER] ONE SIZE 상품 → 사이즈표 스킵")
            else:
                size_html_raw = self._fetch_size_chart_by_sizes(
                    product_code,
                    [merged_sizes[name] for name in merged_sizes_order],
                    scraper
                )
                headers, rows = self.extract_raw_size_chart(size_html_raw)
        else:
            size_html_raw = ""
            headers, rows = [], []


        # ---------------------------------------------------
        # 5) colors 보강
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
        # 6) 옵션 그룹
        # ---------------------------------------------------
        option_groups = []

        if final_colors:
            option_groups.append({
                "group_name": "색상",
                "values": [
                    {
                        "name": c["name"],
                        "code": c["code"],
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

        # ---------------------------------------------------
        # 7) 최종 반환
        # ---------------------------------------------------
        return {
            "original_name": raw_name,
            "colors": final_colors,
            "prices": merged_prices,
            "sizes": [merged_sizes[name] for name in merged_sizes_order],
            "images": sub_images + feature_images,
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


    def _fetch_size_chart_by_sizes(self, product_code, sizes, scraper):
        if not sizes:
            return ""

        size_rows = {}          # 실제 테이블 행 데이터 저장
        size_html_cache = {}    # 캐시용
        header_row = None

        # -----------------------------------------------------------
        # 1) 최적화된 호출 로직: 3개 단위로 건너뛰며 요청
        # -----------------------------------------------------------
        # sizes가 [XS, S, M, L, XL, XXL, 3XL] 일 때 
        # idx 1(S), 4(XL), 6(마지막) 번째 위주로 호출하여 전후 데이터를 다 긁어옴
        target_indices = []
        num_sizes = len(sizes)
        
        for i in range(1, num_sizes, 3):  # 1, 4, 7... 번째 인덱스 추가
            target_indices.append(i)
        
        # 마지막 사이즈가 누락되지 않도록 확인 (예: 사이즈가 7개인데 위 루프가 4에서 끝날 경우)
        if (num_sizes - 1) not in target_indices:
            target_indices.append(num_sizes - 1)

        for idx in target_indices:
            s = sizes[idx]
            size_code = s.get("code")
            
            if not size_code or size_code in size_html_cache:
                continue

            html = scraper.request_size_html(product_code, size_code)
            if not html:
                continue

            size_html_cache[size_code] = html
            soup = BeautifulSoup(html, "html.parser")
            table = soup.select_one("table.dataTable")
            if not table:
                continue

            rows = table.select("tbody tr")
            for r_idx, tr in enumerate(rows):
                # 헤더 확보 (첫 호출 시 1회만)
                if r_idx == 0 and not header_row:
                    header_row = tr
                    header_row.attrs.pop("class", None)
                    continue

                th = tr.find("th")
                if not th: continue

                # 셀 내부 줄바꿈 처리 (기존 로직 유지)
                for td in tr.find_all("td"):
                    cell_text = td.get_text(separator="\n", strip=True) 
                    td.clear()
                    td.append(cell_text) 

                size_name = th.get_text(strip=True)
                # 이미 수집된 사이즈 이름이 아닐 때만 저장 (중복 수집 방지)
                if size_name and size_name not in size_rows:
                    tr.attrs.pop("class", None)
                    size_rows[size_name] = tr

        if not header_row or not size_rows:
            return ""

        # -----------------------------------------------------------
        # 2) 최종 테이블 조립 (기존 순서대로 정렬)
        # -----------------------------------------------------------
        first_html = next(iter(size_html_cache.values()))
        base_soup = BeautifulSoup(first_html, "html.parser")
        base_table = base_soup.select_one("table.dataTable")
        tbody = base_table.find("tbody")
        tbody.clear()

        tbody.append(header_row)

        # 원본 sizes 리스트 순서에 맞춰서 행 추가
        for s in sizes:
            name = s.get("name")
            if name in size_rows:
                tbody.append(size_rows[name])

        return str(base_table)




    # ------------------------------------------------------
    def extract_uniqlo_name_soup(self, soup):
        h1 = soup.select_one("h1 span.title")
        if h1:
            return h1.get_text(strip=True)

        og = soup.select_one("meta[property='og:title']")
        if og:
            return og.get("content")

        return None


    # ------------------------------------------------------
    def _parse_color_list(self, soup):
        colors = []

        for css in self.rules["color"]:
            inputs = soup.select(css)

            for inp in inputs:
                code = inp.get("value")
                if not code:
                    continue

                label = soup.select_one(f"label[for='{inp.get('id')}']")
                if not label:
                    continue

                name = label.get_text(strip=True)

                chip = None
                style = label.get("style", "")
                m = re.search(r'url\(["\']?(.*?)["\']?\)', style)
                if m:
                    chip = m.group(1)

                colors.append({
                    "name": name,
                    "code": code,
                    "chip_image": chip
                })

        return colors


    # ------------------------------------------------------
    def _parse_variant_detail(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return {
            "price": self._parse_price(soup),
            "images": self._parse_images(soup),
            "sizes": self._parse_sizes(soup)
        }

    # ------------------------------------------------------
    def _parse_price(self, soup):
        for css in self.rules["price"]:
            node = soup.select_one(css)
            if node:
                txt = node.get_text(strip=True)
                if txt:
                    return txt
        return ""

    # ------------------------------------------------------
    def _parse_video(self, soup):
        video_tag = soup.find("video")
        if not video_tag:
            return None
        url = video_tag.get("data-src") or video_tag.get("src")
        if url and url.startswith("http"):
            return url
        return None

    # ------------------------------------------------------
    def _parse_images(self, soup):
        images = []

        for css in self.rules["image_main"]:
            for img in soup.select(css):
                url = img.get("src") or img.get("data-src")
                if url and url.startswith("http"):
                    clean = remove_query(url)
                    if clean.lower().endswith(IMAGE_EXT):
                        images.append(clean)

        for css in self.rules["image_feature"]:
            for img in soup.select(css):
                url = img.get("data-src") or img.get("src")
                if url and url.startswith("http"):
                    clean = remove_query(url)
                    if clean.lower().endswith(IMAGE_EXT):
                        images.append(clean)

        return list(dict.fromkeys(images))

    # ------------------------------------------------------
    def _parse_sizes(self, soup):
        sizes = []

        for css in self.rules["size"]:
            for btn in soup.select(css):
                label = soup.select_one(f"label[for='{btn.get('id')}']")
                name = label.get_text(strip=True) if label else None
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

    # ------------------------------------------------------
    def _parse_detail_description(self, soup):
        detail_rules = self.rules.get("detail", {})

        def collect_all(selector):
            if not selector:
                return ""

            selectors = selector if isinstance(selector, list) else [selector]

            texts = []
            for sel in selectors:
                nodes = soup.select(sel)
                for n in nodes:
                    t = n.get_text(" ", strip=True)
                    if t:
                        texts.append(t)

            return " ".join(texts)

        parts = []

        if detail_rules.get("features"):
            t = collect_all(detail_rules["features"])
            if t:
                parts.append(t)

        if detail_rules.get("spec"):
            t = collect_all(detail_rules["spec"])
            if t:
                parts.append(t)

        if detail_rules.get("material"):
            t = collect_all(detail_rules["material"])
            if t:
                parts.append(t)


        if not parts:
            return ""

        # 최종 텍스트 병합
        text = "\n\n".join(parts).strip()
        
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
    
    
    

    def extract_raw_size_chart(self, html: str):
        """
        VN size page HTML → header / rows 추출
        """
        if not html:
            return [], []

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", class_="dataTable") or soup.find("table")
        if not table:
            return [], []

        rows = []
        for tr in table.find_all("tr"):
            cells = [
                c.get_text(strip=True)
                for c in tr.find_all(["th", "td"])
            ]
            if cells:
                rows.append(cells)

        if len(rows) < 2:
            return [], []

        headers = rows[0]
        body_rows = rows[1:]

        return headers, body_rows

    
    def _detect_soldout(self, soup):
        # 1) 전체 상품 품절
        soldout_msg = soup.select_one("div.fr-text-annotation.caution")
        if soldout_msg:
            text = soldout_msg.get_text(strip=True).lower()
            if "out of stock" in text:
                return True

        # 2) 개별 사이즈 품절 여부는 size 파싱에서 처리
        return False

