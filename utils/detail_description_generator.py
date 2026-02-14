# -*- coding: utf-8 -*-
# detail_description_generator.py
# 템플릿 기반 상세설명 HTML 생성기 (FINAL VERSION)
# 구조: templates/detail_template.html + 치환기

from bs4 import BeautifulSoup
from utils.utils_translator import translate_to_korean
import re, os, json
import time
from PIL import Image
import tempfile
from playwright.sync_api import sync_playwright
from utils.path import p
from image_tools.image_source_resolver import resolve_item_image_sources

TEMPLATE_PATH = p("templates", "detail_template.html")

# ---- 전역 캐시: 같은 헤더 반복 번역 방지 ----
HEADER_TRANSLATE_CACHE = {}

# ---- 헤더 매핑 파일 로드 ----
MAPPING_PATH = p("templates", "size_header_mapping.json")
if os.path.exists(MAPPING_PATH):
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        HEADER_MAPPING = json.load(f)
else:
    HEADER_MAPPING = {}   # fallback

def translate_header(text: str) -> str:
    """Translate header text using mapping or cached translation."""
    if not text:
        return ""

    if text in HEADER_TRANSLATE_CACHE:
        return HEADER_TRANSLATE_CACHE[text]

    if text in HEADER_MAPPING:
        HEADER_TRANSLATE_CACHE[text] = HEADER_MAPPING[text]
        return HEADER_MAPPING[text]

    ko = translate_to_korean(text)
    HEADER_TRANSLATE_CACHE[text] = ko
    return ko


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def limit_length(text, max_len=20):
    """Truncate product name to max_len characters."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip()


def normalize_size_chart(headers, body_rows):
    """Normalize raw size chart into translated, formatted HTML."""

    if not headers or not body_rows:
        return ""

    # ------------------------------------------
    # 1) 헤더 번역 (기존 로직 유지)
    # ------------------------------------------
    translated_header = [translate_header(h) for h in headers]

    # ------------------------------------------
    # 2) HTML 구조 생성 (기존 로직 유지)
    # ------------------------------------------
    html_rows = []

    # HEADER
    html_rows.append(
        "<tr>" +
        "".join([
            "<th style='border:2px solid #888;padding:10px;"
            "font-size:20px;font-weight:bold;text-align:center;"
            "background:#f5f5f5;'>" +
            h +
            "</th>"
            for h in translated_header
        ]) +
        "</tr>"
    )

    # BODY
    for row in body_rows:
        html_rows.append(
            "<tr>" +
            "".join([
                "<td style='border:2px solid #ccc;padding:10px;"
                "font-size:18px;text-align:center;'>" +
                col +
                "</td>"
                for col in row
            ]) +
            "</tr>"
        )

    # ------------------------------------------
    # 3) 최종 HTML 반환
    # ------------------------------------------
    final_html = f"""
    <div style="width:100%;margin-bottom:60px">
        <table style="border-collapse:collapse; width:100%;">
            {''.join(html_rows)}
        </table>
    </div>
    """

    return final_html.strip()



# ============================================================
# 3) HTML 블록 생성기
# ============================================================

def render_product_images(image_list):
    """상품 이미지 목록 렌더링"""
    out = []
    for url in image_list:
        if isinstance(url, str) and os.path.exists(url):
            url = "file:///" + url.replace("\\", "/")
        out.append(f"""
        <div style="text-align:center">
            <img src="{url}" style="max-width: 100%; object-fit: contain;">
        </div>
        """)
    return "\n".join(out)


def render_description_section(title, lines):
    """상품설명/소재/사양/색상 공통 섹션"""
    if not lines:
        return ""

    html = []
    html.append(f'<div style="text-align:center"><strong>{title}</strong></div>')

    for t in lines:
        t = clean_text(t)
        html.append(f'<div style="text-align:center">{t}</div>')

    html.append('<div style="text-align:center"><br></div>')
    html.append('<div style="text-align:center"><br></div>')

    return "\n".join(html)


import base64
from image_tools.image_fetcher import fetch_image_content  # 통합 이미지 다운로더

def render_options_section(option_groups, item=None):
    if not option_groups:
        return ""

    url_to_file = {}
    if item is not None:
        logo_results = getattr(item, "logo_job_results", None)
        if isinstance(logo_results, list):
            for r in logo_results:
                url = r.get("url")
                fp = r.get("file_path")
                if url and fp and isinstance(fp, str) and os.path.exists(fp):
                    url_to_file[url] = fp

    rows = []

    # 옵션표는 "이미지 있는 옵션값"만 1개 카드로 렌더링한다.
    # (사이즈 등 이미지 없는 옵션은 제외)
    for group in option_groups:
        values = group.get("values", [])
        if not values:
            continue

        for opt in values:
            name = opt.get("name", "")
            image_url = opt.get("image", "")
            if not image_url:
                continue

            # --- 옵션 이미지 Base64 변환 ---
            img_tag_src = image_url  # 기본값 URL
            
            if image_url:
                local_path = None
                if image_url in url_to_file:
                    local_path = url_to_file[image_url]
                elif os.path.exists(image_url):
                    local_path = image_url

                if local_path:
                    try:
                        with open(local_path, "rb") as f:
                            content = f.read()
                        ext = os.path.splitext(local_path)[1].lower().lstrip(".") or "png"
                        if ext == "jpg":
                            ext = "jpeg"
                        b64_data = base64.b64encode(content).decode("utf-8")
                        img_tag_src = f"data:image/{ext};base64,{b64_data}"
                        content = None
                    except Exception:
                        content = None

                if not local_path:
                    # 무인상품 이미지 차단 대응을 위해 서버에서 직접 가져옴
                    content = fetch_image_content(image_url)
                    if content:
                        # 바이너리 데이터를 Base64 문자열로 변환
                        b64_data = base64.b64encode(content).decode("utf-8")
                        # 이미지 확장자 추출 (기본값 jpg)
                        ext = "jpeg" if "jpg" in image_url.lower() or "jpeg" in image_url.lower() else "png"
                        img_tag_src = f"data:image/{ext};base64,{b64_data}"
            # ------------------------------------

            rows.append(f"""
            <table border="1" style="border-collapse: collapse; width: 100%; margin-bottom: 25px;">
                <tbody>
                    <tr>
                        <td style="padding: 10px; text-align: center; width: 100%;">
                            <img src="{img_tag_src}"
                                 style="max-width: 100%; object-fit: contain;">
                        </td>
                    </tr>
                    <tr style="border-bottom: 3px double;">
                        <td style="text-align: center; padding: 10px;">
                            <strong style="font-size: 1.2rem;">{name}</strong>
                        </td>
                    </tr>
                </tbody>
            </table>
            """)

    return "\n".join(rows)


def split_tall_option_chart(path: str, max_chunk_height: int = 2400):
    """
    Keep original resolution, but split very tall option chart for
    preview/render stability and parity with Windly paste behavior.
    """
    if not path or not os.path.exists(path):
        return [path] if path else []

    try:
        with Image.open(path) as im:
            w, h = im.size
            if h <= max_chunk_height:
                return [path]

            out = []
            y = 0
            idx = 1
            base_dir = os.path.dirname(path)
            stem = os.path.splitext(os.path.basename(path))[0]

            while y < h:
                y2 = min(y + max_chunk_height, h)
                part = im.crop((0, y, w, y2))
                part_path = os.path.join(base_dir, f"{stem}_part{idx:02d}.png")
                part.save(part_path, format="PNG")
                out.append(part_path.replace("\\", "/"))
                y = y2
                idx += 1

        print(f"[OPTIONS_CHART] split for preview: {os.path.basename(path)} -> {len(out)} parts")
        return out
    except Exception as e:
        print(f"[OPTIONS_CHART][WARN] preview split failed: {e}")
        return [path]


# ============================================================
# 4) 메인 생성 함수: generate_detail_html(item)
# ============================================================

def generate_detail_html(item):
    """
    ProductItem 기반 상세설명 HTML 생성
    item 필드:
      - item.final_name
      - item.images (list)
      - item.description (str)
      - item.options (list[{name,image}])
      - item.size_html (size chart HTML 문자열)
    """

    # ----------------------------------------------------
    # A) 템플릿 로드
    # ----------------------------------------------------
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"템플릿 파일 없음: {TEMPLATE_PATH}")

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # ----------------------------------------------------
    # B) 상품명 20자 축약
    # ----------------------------------------------------
    name_40 = getattr(item, "final_name", "") or ""
    
    # ----------------------------------------------------
    # C) 영상 섹션 (다운로드/분석 X, 준비된 mp4만 사용)
    # ----------------------------------------------------
    video_section = ""
    if getattr(item, "video_file", None):
        file_url = "file:///" + item.video_file.replace("\\", "/")
        video_section = f"""
        <div style="text-align:center; margin:40px 0;">
            <video controls playsinline style="max-width:100%; height:auto;">
                <source src="{file_url}" type="video/mp4">
            </video>
        </div>
        """

    # ----------------------------------------------------
    # C) 상품 이미지
    # ----------------------------------------------------
    images = resolve_item_image_sources(item)
    product_images_html = render_product_images(images)

    # ----------------------------------------------------
    # D) 상품설명: 번역 + 요약
    # ----------------------------------------------------
    detail_html = (item.final_detail_html or "").replace("\n", "<br>")
    # 줄바꿈 정리 + HTML 변환
    if detail_html:
        description_section = f"""
        <div style="text-align:center; line-height:1.7;margin-top:30px;margin-bottom:30px">
            {detail_html}
        </div>
        <div style="text-align:center"><br></div>
        <div style="text-align:center"><br></div>
        """
    else:
        description_section = ""

    # ----------------------------------------------------
    # F) 옵션 섹션
    # ----------------------------------------------------
    options = item.parsed_raw.get("options", [])
    option_chart_paths = []
    card_idx = 1

    # 옵션 카드 1개당 캡처 이미지 1개 생성
    for group in options:
        values = group.get("values", []) if isinstance(group, dict) else []
        for value in values:
            if not isinstance(value, dict):
                continue
            if not value.get("image"):
                continue

            single_group = [
                {
                    "group_name": group.get("group_name", ""),
                    "values": [value],
                }
            ]
            card_html = render_options_section(single_group, item=item)
            if not card_html.strip():
                continue

            out_name = f"options_card_{card_idx:03d}.png"
            card_path = html_to_png_options(card_html, output_name=out_name)
            option_chart_paths.append(card_path)
            card_idx += 1

    item.options_chart_paths = option_chart_paths
    item.options_chart_path = option_chart_paths[0] if option_chart_paths else None

    if option_chart_paths:
        options_section = "\n".join(
            [
                f"""
        <div style="text-align:center; margin:50px 0;">
            <img src="{p}" style="max-width:100%; object-fit:contain;">
        </div>
                """.rstrip()
                for p in option_chart_paths
            ]
        )
    else:
        options_section = ""

    # ----------------------------------------------------
    # G) BOTTOM_SECTION (사이즈표 HTML + bottom_image)
    # ----------------------------------------------------
    raw_size_html = getattr(item, "size_html", "") or item.parsed_raw.get("size_html", "")
    
    # 사이즈표 이미지 생성
    if raw_size_html:
        size_chart_img_path = html_to_png_final(raw_size_html)
        item.size_chart_image_path = size_chart_img_path
        size_chart_section = f"""
        <div style="text-align:center; margin:50px 0;">
            <img src="{size_chart_img_path}" style="max-width:100%; object-fit:contain;">
        </div>
        """
    else:
        size_chart_section = ""
        
    # ----------------------------------------------------
    # I) 이미지 접근 경로 생성 (Chrome file:/// 용)
    # ----------------------------------------------------
    IMAGES_DIR = p("images").replace("\\", "/")
    IMG_PATH = IMAGES_DIR.replace("\\", "/")    # f-string 이전 버전 호환

    TOP_IMAGE = f"file:///{IMG_PATH}/top_image.jpg"
    BOTTOM_IMAGE = f"file:///{IMG_PATH}/bottom_image.jpg"

    # ----------------------------------------------------
    # H) 템플릿 변수를 실제 데이터로 치환
    # ----------------------------------------------------
    final_html = (
        template
        .replace("{{TOP_IMAGE}}", TOP_IMAGE)
        .replace("{{PRODUCT_NAME}}", name_40)
        .replace("{{VIDEO_SECTION}}", video_section)
        .replace("{{PRODUCT_IMAGES}}", product_images_html)
        .replace("{{DESCRIPTION_SECTION}}", description_section)
        .replace("{{SIZE_CHART_SECTION}}", size_chart_section)
        .replace("{{OPTIONS_SECTION}}", options_section)
        .replace("{{BOTTOM_IMAGE}}", BOTTOM_IMAGE)
    )

    return final_html.strip()


def html_to_png_options(options_html: str, width=720, output_name="options_section.png"):
    import os, threading
    from playwright.sync_api import sync_playwright

    WINDLY_TEMP_DIR = p("windly_temp")
    if not os.path.exists(WINDLY_TEMP_DIR):
        os.makedirs(WINDLY_TEMP_DIR)

    # HTML 경로 windly_temp
    html_path = p("windly_temp", "options_src.html")

    # full_html 구성
    full_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, sans-serif;
                background-color: white;
            }}
            img {{
                image-rendering: -webkit-optimize-contrast; 
                display: block;
                margin: 0 auto;
            }}
            table {{
                border-color: #eee; /* 테두리 색상을 약하게 */
            }}
            #options-root {{
                margin: 0;
                padding: 0;
            }}
        </style>
    </head>
    <body>
        <div id="options-root">
            {options_html}
        </div>
    </body>
    </html>
    """

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    # PNG 경로
    png_path = p("windly_temp", output_name)

    # screenshot 코드 변경 금지
    result = {'path': None, 'error': None}

    def worker():
        try:
            with sync_playwright() as p_auth:
                browser = p_auth.chromium.launch()
                # device_scale_factor=2 (고해상도)
                page = browser.new_page(
                    viewport={"width": width, "height": 1200},
                    device_scale_factor=2 
                )

                page.goto("file:///" + html_path.replace("\\", "/"))
                
                # 이미지 로딩 완료 대기
                page.wait_for_load_state('networkidle') 

                root = page.locator("#options-root")
                # 콘텐츠 영역만 스크린샷 (불필요한 하단 여백 제거)
                root.screenshot(path=png_path, animations="disabled")

                browser.close()
            result['path'] = png_path.replace("\\", "/")
        except Exception as e:
            result['error'] = e

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    if result['error']:
        raise result['error']

    return result['path']


def html_to_png_final(html: str, width=720, output_name=None, max_retry=2):
    import os, threading, time
    from playwright.sync_api import sync_playwright

    WINDLY_TEMP_DIR = p("windly_temp")
    if not os.path.exists(WINDLY_TEMP_DIR):
        os.makedirs(WINDLY_TEMP_DIR)

    html_path = p("windly_temp", "size_chart_src.html")

    cleaned_html = html.replace("margin-bottom:60px", "margin-bottom:0px")

    full_html = f"""
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
      </style>
    </head>
    <body>
      {cleaned_html}
    </body>
    </html>
    """

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    if not output_name:
        output_name = "size_chart.png"

    png_path = p("windly_temp", output_name)

    last_error = None

    for attempt in range(1, max_retry + 1):
        result = {"error": None}

        def worker():
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch()
                    page = browser.new_page(
                        viewport={"width": width, "height": 2000}
                    )

                    page.goto("file:///" + html_path.replace("\\", "/"))
                    page.wait_for_load_state("domcontentloaded")

                    table = page.locator("body table")

                    # table 로딩 대기
                    table.wait_for(state="visible", timeout=2000)

                    table.screenshot(path=png_path)
                    browser.close()
            except Exception as e:
                result["error"] = e

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        if not result["error"] and os.path.exists(png_path):
            return png_path.replace("\\", "/")

        last_error = result["error"]
        print(f"[SIZE_CHART] attempt {attempt}/{max_retry} failed -> retrying...")
        time.sleep(0.4)  # 짧은 대기 후 재시도

    # 최종 실패
    raise last_error

