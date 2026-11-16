# parsers/muji/parser_jp.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.detail_description_generator import normalize_size_chart

import time
import re
import json
from typing import Any, Dict, List, Optional
import hashlib
from image_tools.image_fetcher import fetch_image_content

def _now():
    return time.strftime("%H:%M:%S")

def _log(tag: str, msg: str):
    print(f"[{_now()}][MUJI][{tag}] {msg}")

def _short(s: Optional[str], n: int = 160) -> str:
    if not s:
        return ""
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + "..."

def _dump(obj, n=3):
    try:
        if isinstance(obj, list):
            return json.dumps(obj[:n], ensure_ascii=False)
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


class MujiJapanParser:

    def __init__(self, rules, brand):
        self.rules = rules
        self.brand = brand

    def parse(self, scraper, original_url, first_html):
        t0 = time.time()
        _log("START", f"url={original_url}")
        
        # 1. RAW 데이터(첫 번째 탭: 상세설명) 파싱
        soup = BeautifulSoup(first_html, "html.parser")
        raw_name = self._parse_name(soup)
        detail_description = self._parse_detail_description(soup)
        
        # 2. 색상 목록 먼저 추출 (이 URL들이 있어야 SIZE_CHART와 COLOR 호출 가능)
        colors = self._parse_color_list(soup)

        # 3) 사이즈표 전용 요청 (탭 전환 모드)
        # original_url을 사용하여 'SIZE_CHART' 모드로 한 번 더 호출합니다.
        _log("REQ_SIZE", "Requesting size chart tab...")
        size_html_content = scraper.request_size_chart(original_url) # name 대신 url 전달
        
        if size_html_content:
            soup_size_chart = BeautifulSoup(size_html_content, "html.parser")
            size_html_raw = self._parse_size_chart(soup_size_chart)
            headers, rows = self.extract_raw_size_chart(size_html_raw)
            _log("SIZECHART", f"Success: rows={len(rows)}")
        else:
            _log("SIZECHART_FAIL", "Could not fetch size chart tab")
            size_html_raw, headers, rows = "", [], []
        
        # 4) 변수 초기화
        results = {"variants": {}, "detail_description": detail_description}

        # 5) 색상별 상세 데이터 요청 (이미지/가격/재고)
        seen = set()
        for idx, c in enumerate(colors):
            name = c.get("name")
            v_url = c.get("url")

            if not v_url or v_url in seen:
                continue
            seen.add(v_url)

            # 각 색상별 페이지 요청
            v_html = scraper.request_color_html(v_url, name)
            if not v_html:
                continue

            soup_variant = BeautifulSoup(v_html, "html.parser")

            price = self._parse_price(soup_variant)
            imgs = self._parse_images(soup_variant)
            sizes = self._parse_sizes(soup_variant)

            _log("VARIANT", f"name={name} price={price}")
            _log(
                "VARIANT",
                f"name={name} images_count={len(imgs)} "
                f"first={imgs[0] if imgs else None}"
            )
            _log(
                "VARIANT",
                f"name={name} sizes_count={len(sizes)} "
                f"sample={_dump(sizes, n=6)}"
            )

            results["variants"][name] = {
                "price": price,
                "images": imgs,
                "sizes": sizes
            }

        _log("VARIANTS_DONE", f"variant_count={len(results['variants'])}")

        # 6) 병합
        merged_sizes = {}
        merged_sizes_order = []
        merged_prices = {}
        final_images = []

        # 내용(Hash) 기반 중복 체크용 셋
        seen_img_hashes = set()

        for color_name, v in results["variants"].items():
            merged_prices[color_name] = v.get("price", "")

            for img_url in v.get("images", []):
                # 1. 이미지를 실제로 가져옴 (HTTP/2 + MUJI 우회 로직 작동)
                content = fetch_image_content(img_url)
                
                if content:
                    # 2. 이미지 데이터의 고유 지문(MD5) 생성
                    img_hash = hashlib.md5(content).hexdigest()

                    # 3. 지문이 처음 보는 것이라면 추가
                    if img_hash not in seen_img_hashes:
                        seen_img_hashes.add(img_hash)
                        final_images.append(img_url)
                    else:
                        print(f"[PARSER] 내용 중복 이미지 제외: {img_url.split('/')[-1]}")
                else:
                    print(f"[PARSER] 이미지 로드 실패로 건너뜀: {img_url[:50]}")

            for s in v.get("sizes", []):
                nm = s.get("name")
                if not nm:
                    continue

                if nm not in merged_sizes:
                    merged_sizes[nm] = s
                    merged_sizes_order.append(nm)
                else:
                    if s.get("disabled"):
                        merged_sizes[nm]["disabled"] = True
        
        final_images = self.sort_muji_images(final_images)

        _log("MERGE", f"prices_count={len(merged_prices)}")
        _log("MERGE", f"sizes_count={len(merged_sizes_order)} sizes={merged_sizes_order}")
        _log(
            "MERGE",
            f"images_count={len(final_images)} "
            f"first={final_images[0] if final_images else None}"
        )

        # 7) 옵션 그룹
        option_groups = []

        if colors:
            color_values = []
            for c in colors:
                c_name = c.get("name")
                # 각 색상(variant)의 첫 번째 이미지를 대표 이미지로 사용
                variant_data = results["variants"].get(c_name, {})
                variant_images = variant_data.get("images", [])
                representative_image = variant_images[0] if variant_images else ""

                color_values.append({
                    "name": c_name,
                    "disabled": False,
                    "image": representative_image,
                    "chip_image": c.get("chip_image")
                })

            option_groups.append({
                "group_name": "색상",
                "values": color_values
            })

        if merged_sizes_order:
            option_groups.append({
                "group_name": "사이즈",
                "values": [
                    {
                        "name": merged_sizes[nm]["name"],
                        "disabled": merged_sizes[nm]["disabled"]
                    }
                    for nm in merged_sizes_order
                ]
            })

        _log(
            "OPTIONS",
            f"groups={len(option_groups)} "
            f"group_names={[g['group_name'] for g in option_groups]}"
        )
        _log("END", f"elapsed_ms={int((time.time() - t0) * 1000)}")

        return {
            "original_name": raw_name,
            "prices": merged_prices,
            "sizes": [merged_sizes[name] for name in merged_sizes_order],
            "images": final_images,
            "detail_description": detail_description.get("text", ""),
            "model_number": detail_description.get("model_number"),
            "size_html_raw": size_html_raw,
            "options": option_groups,
            "size_headers_original": headers,
            "size_rows_original": rows
        }

    # 6-1) 이미지 순서 조정 (순번 우선 정렬)
    def sort_muji_images(self, image_urls):
        def extract_sort_key(url):
            # 파일명만 추출 (예: 4547315778225_01_org.jpg)
            filename = url.split('/')[-1]
            
            # 1. 순번 추출 ( _01, _02 등 )
            # _(숫자)_ 구조를 찾습니다. 없으면 메인컷이므로 "00"으로 처리
            order_match = re.search(r'_(\d{2})_', filename)
            order = order_match.group(1) if order_match else "00"
            
            # 2. 상품 고유 번호 추출 (앞부분 숫자)
            product_id = filename.split('_')[0]
            
            # (순번, 상품번호) 순으로 키를 반환하여 순번이 같은 것끼리 먼저 모이게 함
            return (order, product_id)

        return sorted(image_urls, key=extract_sort_key)

    # ---------------------------------------------------
    # 상품명
    # ---------------------------------------------------
    def _parse_name(self, soup):
        node = soup.select_one("h1.ProductsH1_title__tuW0O")
        return node.get_text(strip=True) if node else None

    # ---------------------------------------------------
    # 색상 목록 (이름 + URL)
    # ---------------------------------------------------
    # ---------------------------------------------------
    # 색상 목록 (이름 + URL + 컬러칩)
    # ---------------------------------------------------
    def _parse_color_list(self, soup):
        root = soup.select_one("div.ProductColorButton_colors__XGUaH")
        colors = []
        # a[title] 노드들을 찾습니다.
        nodes = soup.select("div.ProductColorButton_colors__XGUaH a[title]")

        import re
        for a in nodes:
            name = a.get("title")
            href = a.get("href")
            
            # 컬러칩 이미지 추출 (span의 style 속성에서 url 추출)
            chip_image = None
            span = a.select_one("span.ColorButton_colorButtonSpan__GddtQ")
            if span and span.get("style"):
                style = span.get("style")
                # url('...') 또는 url(...) 형태에서 주소만 추출
                match = re.search(r'url\((["\']?)(.*?)\1\)', style)
                if match:
                    chip_image = match.group(2)

            if name and href:
                colors.append({
                    "name": name, 
                    "url": urljoin('https://www.muji.com', href),
                    "chip_image": chip_image # 컬러칩 이미지 추가
                })

        return colors


    # ---------------------------------------------------
    # 가격
    # ---------------------------------------------------
    def _parse_price(self, soup):
        node = soup.select_one("span.ProductPrice_number__amount__kV83j")
        return node.get_text(strip=True) if node else ""

    # ---------------------------------------------------
    # 이미지
    # ---------------------------------------------------
    def _parse_images(self, soup):
        images = []
        for img in soup.select("img[data-testid='image']"):
            src = img.get("src")
            if src and src.startswith("http"):
                clean = src.split("?")[0]
                if clean.lower().endswith(IMAGE_EXT):
                    images.append(clean)
        return list(dict.fromkeys(images))

    # ---------------------------------------------------
    # 사이즈
    # ---------------------------------------------------
    def _parse_sizes(self, soup):
        sizes = []
        for btn in soup.select("div.SizeButton_button__iiNop"):
            name = btn.get_text(strip=True)
            disabled = "SizeButton_noStock__is0lu" in btn.get("class", [])
            if name:
                sizes.append({
                    "name": name,
                    "disabled": disabled
                })
        return sizes
    
        # ---------------------------------------------------
    # 상세설명
    # ---------------------------------------------------
    def _parse_detail_description(self, soup):

        nodes = soup.select("p.ItemDescription_description__e_erj")
        text = " ".join(n.get_text(" ", strip=True) for n in nodes)

        model_number = None
        import re
        m = re.search(r"商品番号[:：]?\s*([0-9A-Za-z\-]+)", text)
        if m:
            model_number = m.group(1)
            text = re.sub(r"商品番号[:：]?\s*[0-9A-Za-z\-]+", "", text).strip()

        return {
            "text": text,
            "model_number": model_number
        }

    # ---------------------------------------------------
    # 사이즈표 HTML
    # ---------------------------------------------------
    def _parse_size_chart(self, soup):
        table = soup.select_one("div.ProductSpec_sizeTableWrapperTablet__KMlv_ table")
        return str(table) if table else ""

    def extract_raw_size_chart(self, html):
        if not html:
            return [], []

        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            return [], []

        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)

        if len(rows) < 2:
            return [], []

        return rows[0], rows[1:]