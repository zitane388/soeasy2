# parsers/uniqlo/parser_jp.py
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urlsplit, urlunsplit
from utils.detail_description_generator import normalize_size_chart
import os

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


class UniqloJapanParser:

    def __init__(self, rules, brand):
        self.rules = rules
        self.brand = brand

    def parse(self, scraper, original_url, first_html):
        
        soup = BeautifulSoup(first_html, "html.parser")
        
        # ---------------------------------------------------
        # [NEW] 사이즈표 HTML 파싱
        # ---------------------------------------------------
        size_html_raw = self._parse_size_chart(soup)

        # 헤더/행 분리
        headers, rows = self.extract_raw_size_chart(size_html_raw)

        # ① 색상 목록 파싱
        colors = self._parse_color_list(soup)
        print("[UniqloJapanParser] colors =", colors)
            
        # ② 상세설명 파싱 (메인 페이지 기준)
        detail_description = self._parse_detail_description(soup)
        
        
        title_node = soup.find("div", {"data-testid": "ITOTypography"})
        raw_name = title_node.get_text(strip=True) if title_node else None

        # 상품명 파싱 추가
        raw_name = self.extract_uniqlo_name_soup(soup)
        
        video_url = self._parse_video(soup)

        # ③ 임시 구조 저장
        results = {
            "colors": colors,
            "variants": {},
            "detail_description": detail_description
        }

        # ④ 색상별 상세 파싱
        print(f"[DEBUG] 색상 루프 시작 ({len(colors)}개)")
        seen = set()
        for c in colors:
            print(f"[DEBUG] 색상 처리중: {c}")
            code = c["code"]
            name = c["name"]
            if not code:
                continue  # 🔥 code 없는 거 제거
            
            if code in seen:
                continue  # 🔥 중복 색상 제거
            seen.add(code)

            variant_url = replace_color_code(original_url, code)
            print(f"[UniqloJapanParser] 색상 '{name}' 요청 →", variant_url)

            html_variant = scraper.request_color_html(original_url, code)
            if not html_variant:
                print(f"[UniqloJapanParser] {name} HTML 실패")
                continue

            detail = self._parse_variant_detail(html_variant)
            results["variants"][code] = detail
        

        # ------------------------------------------------------
        # 🔥 variants 기반 최종 병합 (정렬 그대로 유지)
        # ------------------------------------------------------
        merged_sizes = {}        
        merged_sizes_order = []  

        merged_prices = {}

        # 이미지 분류용
        color_main_images = {}  # color_code → 대표 item 이미지
        main_images = []
        sub_images = []
        feature_images = []
        seen_sub = set()
        seen_feature = set()

        for color_code in results["variants"].keys():  # colors 순서 그대로
            variant = results["variants"][color_code]

            # 가격 병합
            merged_prices[color_code] = variant.get("price", "")

            # ----------------------------
            # 🔥 이미지 분류 시작
            # ----------------------------
            for url in variant.get("images", []):
                lower = url.lower()

                # 대표 item 이미지
                if "/item/" in lower:
                    if color_code not in color_main_images:
                        color_main_images[color_code] = url
                        main_images.append(url)
                    continue

                # sub 이미지
                if "/sub/" in lower:
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

            # ----------------------------
            # 🔥 사이즈 병합
            # ----------------------------
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
                    # code 업그레이드
                    if merged_sizes[name]["code"] is None and s.get("code"):
                        merged_sizes[name]["code"] = s["code"]

                    # disabled → 하나라도 TRUE면 TRUE
                    if s.get("disabled", False):
                        merged_sizes[name]["disabled"] = True

        # ------------------------------------------------------
        # 🔥 이미지 최종 정렬
        # ------------------------------------------------------
        #
        # [대표 이미지 BLACK]
        # [대표 이미지 OFF WHITE]
        # [대표 이미지 GRAY]
        # [대표 이미지 NAVY]
        #
        # [sub 이미지 1]
        # [sub 이미지 2]
        #
        # [feature 1]
        # [feature 2]
        # [feature 3]
        # [feature 4]
        #
        # ------------------------------------------------------

        color_order = [c["code"] for c in colors]

        # 대표 이미지 색상 순 정렬
        main_images_ordered = [
            color_main_images[c] for c in color_order if c in color_main_images
        ]

        # 최종 이미지
        final_images = main_images + sub_images + feature_images

        # ------------------------------------------------------
        # 🔥 colors에 image 필드 추가
        # ------------------------------------------------------
        final_colors = []
        for c in colors:
            code = c["code"]
            final_colors.append({
                "name": c["name"],
                "code": code,
                "image": color_main_images.get(code),
                "chip_image": c.get("chip_image")
            })
            
        # ------------------------------------------------------
        # 🔥 옵션 그룹 생성 (표준 옵션 구조)
        # ------------------------------------------------------
        option_groups = []

        # 1) 색상 그룹
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

        # 2) 사이즈 그룹
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
            
        detail_data = results["detail_description"]

        # ------------------------------------------------------
        # 🔥 최종 구조 생성 (variants 제거)
        # ------------------------------------------------------
        final_results = {
            "original_name": raw_name,
            "colors": final_colors,
            "prices": merged_prices,
            "sizes": [merged_sizes[name] for name in merged_sizes_order],
            "images": final_images,
            "detail_description": detail_data.get("text", ""),
            "model_number":      detail_data.get("model_number"),
            "options": option_groups,
            "video": video_url,
            "size_headers_original": headers,
            "size_rows_original": rows,
            "size_html_raw": size_html_raw
        }
        
        
        import json
        
        print("\n=========== FINAL PARSED DATA ===========")
        print(json.dumps(final_results, ensure_ascii=False, indent=2))
        print("=========================================\n")

        return final_results
    
    def extract_uniqlo_name_soup(self, soup):
        main = soup.find("main")
        if not main:
            return None
        
        node = main.find("div", {"data-testid": "ITOTypography"})
        return node.get_text(strip=True) if node else None



    # ------------------------------------------------------
    # 1) 색상 목록 파싱
    # ------------------------------------------------------
    def _parse_color_list(self, soup):
        colors = []
        for css in self.rules["color"]:
            for btn in soup.select(css):
                img = btn.find("img")
                name = img.get("alt").strip() if img and img.get("alt") else None
                code = btn.get("value")
                chip = img.get("src") if img else None
                
                if not code:
                    continue

                if name:
                    colors.append({
                        "name": name,
                        "code": code,
                        "chip_image": chip
                    })
        return colors

    # ------------------------------------------------------
    # 2) 색상별 상세 파싱 (가격/이미지/사이즈)
    # ------------------------------------------------------
    def _parse_variant_detail(self, html):
        soup = BeautifulSoup(html, "html.parser")

        return {
            "price": self._parse_price(soup),
            "images": self._parse_images(soup),
            "sizes": self._parse_sizes(soup)
        }

    # ------------------------------------------------------
    # 가격 파싱
    # ------------------------------------------------------
    def _parse_price(self, soup):
        for css in self.rules["price"]:
            node = soup.select_one(css)
            if node:
                txt = node.get_text(strip=True)
                if txt:
                    return txt
        return ""
    
    def _parse_video(self, soup):
        """
        유니클로 상품 상세에 포함된 영상 <video> 태그에서
        data-src 또는 src URL 하나만 찾아서 반환
        """
        video_tag = soup.find("video")
        if not video_tag:
            return None

        url = video_tag.get("data-src") or video_tag.get("src")
        if not url:
            return None

        if not url.startswith("http"):
            return None

        # 영상은 쿼리스트링 유지해야 HLS 정보가 살아있음
        return url


    # ------------------------------------------------------
    # 이미지 파싱 (메인 + feature)
    # ------------------------------------------------------
    def _parse_images(self, soup):
        images = []

        # 메인
        for css in self.rules["image_main"]:
            for img in soup.select(css):
                url = img.get("src") or img.get("data-src")
                if url and url.startswith("http"):
                    url = remove_query(url)
                    # 이미지 확장자 필터링
                    lower = url.lower()
                    if not lower.endswith(IMAGE_EXT):
                        continue
                    images.append(url)

        # 하단 feature
        for css in self.rules["image_feature"]:
            for img in soup.select(css):
                url = img.get("data-src") or img.get("src")
                if url and url.startswith("http"):
                    url = remove_query(url)
                    # 이미지 확장자 필터링
                    lower = url.lower()
                    if not lower.endswith(IMAGE_EXT):
                        continue
                    images.append(url)

        return list(dict.fromkeys(images))

    # ------------------------------------------------------
    # 사이즈 파싱
    # ------------------------------------------------------
    def _parse_sizes(self, soup):
        sizes = []

        for css in self.rules["size"]:
            for btn in soup.select(css):
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
    
    # ------------------------------------------------------
    # 상세설명 파싱 (상세 / 사양 / 소재·손질)
    # ------------------------------------------------------
    def _parse_detail_description(self, soup):
        """
        상세 설명을 수집 → 상품번호 추출/제거 → 
        LLM 입력에 적합한 단일 문자열 + model_number 함께 반환
        """

        detail_rules = self.rules.get("detail", {})

        def collect_all(selector):
            """여러 문단을 모두 합쳐 하나의 문자열로 반환"""
            if not selector:
                return ""

            nodes = soup.select(selector)
            if not nodes:
                return ""

            texts = [n.get_text(" ", strip=True) for n in nodes]
            return " ".join(t for t in texts if t)

        parts = []

        # 1) 특징/상품설명
        features_sel = detail_rules.get("features")
        if features_sel:
            t = collect_all(features_sel)
            if t:
                parts.append(t)

        # 2) 사양
        spec_sel = detail_rules.get("spec")
        if spec_sel:
            t = collect_all(spec_sel)
            if t:
                parts.append(t)

        # 3) 소재
        material_sel = detail_rules.get("material")
        if material_sel:
            t = collect_all(material_sel)
            if t:
                parts.append(t)

        if not parts:
            return {"text": "", "model_number": None}

        # 최종 텍스트 병합
        final_text = "\n\n".join(parts).strip()

        # ============================================
        # 🔥 상품번호 추출 및 제거 (파서에서 처리)
        # ============================================
        import re
        model_number = None

        m = re.search(r"商品番号[:：]?\s*([0-9A-Za-z\-]+)", final_text)
        if m:
            model_number = m.group(1)
            final_text = re.sub(r"商品番号[:：]?\s*([0-9A-Za-z\-]+)", "", final_text).strip()

        return {
            "text": final_text,
            "model_number": model_number
        }


    
    def _parse_size_chart(self, soup: BeautifulSoup):
        """유니클로 사이즈표 HTML 전체를 추출"""
        # 1) table 구조
        table = soup.find("table", class_="size-chart")
        if table:
            return str(table)

        # 2) div 기반 사이즈표
        div = soup.find("div", class_="size-chart")
        if div:
            return str(div)

        # 3) 일부 페이지는 data-testid 사용
        wrapper = soup.find("div", {"data-testid": "size-chart"})
        if wrapper:
            return str(wrapper)

        # 4) 다른 형태도 대비 (Fallback)
        fallback = soup.find("section", id="size-chart")
        if fallback:
            return str(fallback)

        return ""
    
    def extract_raw_size_chart(self, html: str):
        """ size_html_raw 에서 원본 헤더/행을 분리하여 반환 """
        if not html:
            return [], []

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return [], []

        rows = []
        for tr in table.find_all("tr"):
            cols = tr.find_all(["th", "td"])
            cells = [c.get_text(strip=True) for c in cols]
            if cells:
                rows.append(cells)

        if not rows or len(rows) < 2:
            return [], []

        headers = rows[0]
        body_rows = rows[1:]

        return headers, body_rows
