# parsers/uniqlo/parser_jp.py
from parsers.base_parser import BaseParser
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


class UniqloJapanParser(BaseParser):

    def __init__(self, rules):
        self.rules = rules
        print("[UniqloJapanParser] 파서 초기화 완료")

    def parse(self, html: str, request_raw_html=None, original_url=None):
        print("[UniqloJapanParser] parse 시작")
        
        soup = BeautifulSoup(html, "html.parser")
        
        # ---------------------------------------------------
        # [NEW] 사이즈표 HTML 파싱
        # ---------------------------------------------------
        size_html_raw = self._parse_size_chart(soup)
        size_html_final = normalize_size_chart(size_html_raw)

        # ① 색상 목록 파싱
        colors = self._parse_color_list(soup)
        print("[UniqloJapanParser] colors =", colors)
            
        # ② 상세설명 파싱 (메인 페이지 기준)
        detail_description = self._parse_detail_description(soup)

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

            print(f"[DEBUG] request_raw_html 호출전 → {variant_url}")
            html_variant = request_raw_html(variant_url, code)
            print(f"[DEBUG] request_raw_html 반환: {bool(html_variant)}")
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
        final_images = sub_images + feature_images

        # ------------------------------------------------------
        # 🔥 colors에 image 필드 추가
        # ------------------------------------------------------
        final_colors = []
        for c in colors:
            code = c["code"]
            final_colors.append({
                "name": c["name"],
                "code": code,
                "image": color_main_images.get(code)
            })


        # ------------------------------------------------------
        # 🔥 최종 구조 생성 (variants 제거)
        # ------------------------------------------------------
        final_results = {
            "colors": final_colors,  # 대표 이미지 포함
            "prices": merged_prices,
            "sizes": [merged_sizes[name] for name in merged_sizes_order],
            "images": final_images,
            "detail_description": results["detail_description"],
            "size_html": size_html_final
        }

        return final_results



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
                url = img.get("src")
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
        상세 설명 파트를 수집하여 LLM이 처리하기 좋은
        단일 문자열 형태로 합쳐 반환한다.
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

        # ---------------------------------------
        # 🔥 최종: parts 를 하나의 문자열로 합침
        # ---------------------------------------
        if not parts:
            return ""

        # 문단 간 두 줄바꿈으로 자연스러운 구분
        final_text = "\n\n".join(parts).strip()
        return final_text

    
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


