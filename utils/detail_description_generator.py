# detail_description_generator.py
# 템플릿 기반 상세설명 HTML 생성기 (FINAL VERSION)
# 구조: templates/detail_template.html + 이 치환기

from bs4 import BeautifulSoup
from utils.utils_translator import translate_to_korean
import re, os, json
import time
from PIL import Image
import tempfile
from playwright.sync_api import sync_playwright

TEMPLATE_PATH = os.path.join("templates", "detail_template.html")

# ---- 전역 캐시: 같은 헤더는 반복 번역하지 않음 ----
HEADER_TRANSLATE_CACHE = {}

# ---- 매핑 파일 로드 ----
MAPPING_PATH = os.path.join("templates", "size_header_mapping.json")
if os.path.exists(MAPPING_PATH):
    with open(MAPPING_PATH, "r", encoding="utf-8") as f:
        HEADER_MAPPING = json.load(f)
else:
    HEADER_MAPPING = {}   # fallback

def translate_header(text: str) -> str:
    """헤더 텍스트 → 매핑 적용 → 없으면 Google 번역 → 캐시에 저장"""
    if not text:
        return ""

    # 캐시 먼저 확인
    if text in HEADER_TRANSLATE_CACHE:
        return HEADER_TRANSLATE_CACHE[text]

    # 매핑표에 있으면 그대로 사용
    if text in HEADER_MAPPING:
        HEADER_TRANSLATE_CACHE[text] = HEADER_MAPPING[text]
        return HEADER_MAPPING[text]

    # 매핑 없으면 Google 번역
    ko = translate_to_korean(text)

    # 번역이 너무 이상하면 원문을 그대로 살리는 조건도 가능 (원하면 추가)
    HEADER_TRANSLATE_CACHE[text] = ko
    return ko

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def limit_length(text, max_len=20):
    """상품명을 20자 내로 축약"""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip()


def normalize_size_chart(headers, body_rows):
    """
    extract_raw_size_chart 에서 이미 분리된
    headers, body_rows를 기반으로
    번역 + 정규화된 표 HTML을 생성한다.
    """

    if not headers or not body_rows:
        return ""

    # ------------------------------------------
    # 1) 헤더 번역 (기존 로직 유지)
    # ------------------------------------------
    translated_header = [translate_header(h) for h in headers]

    # ------------------------------------------
    # 2) HTML 표 재구성 (기존 로직 유지)
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
    """상품 전체 이미지 나열"""
    out = []
    for url in image_list:
        out.append(f"""
        <div style="text-align:center">
            <img src="{url}" style="max-width: 100%; object-fit: contain;">
        </div>
        """)
    return "\n".join(out)


def render_description_section(title, lines):
    """상품설명·소재·사양·세탁 등 공통 섹션"""
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


def render_options_section(option_groups):
    """
    option_groups 형식:
    [
        {
            "group_name": "색상",
            "values": [
                {"name": "...", "image": "..."},
                ...
            ]
        }
    ]

    ※ 색상 그룹만 처리하며 타이틀은 출력하지 않음.
    """

    if not option_groups:
        return ""

    html_parts = []

    for group in option_groups:
        group_name = group.get("group_name", "")
        values = group.get("values", [])

        # 색상 그룹만 처리
        if "색" not in group_name:
            continue

        rows = []
        for opt in values:
            name = opt.get("name", "")
            image = opt.get("image", "")

            rows.append(f"""
            <table border="1" style="border-collapse: collapse; width: 100%; margin-bottom: 25px;">
                <tbody>

                    <tr>
                        <td style="padding: 10px; text-align: center; width: 100%;">
                            <img src="{image}"
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

        html_parts.append("\n".join(rows))

    return "\n".join(html_parts)


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
    # C) 영상 섹션 (다운로드/분석 X — 이미 준비된 mp4만 사용)
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
    images = getattr(item, "images", []) or item.parsed_raw.get("images", [])
    product_images_html = render_product_images(images)

    # ----------------------------------------------------
    # D) 상품설명: 번역 + 요약
    # ----------------------------------------------------
    detail_html = (item.final_detail_html or "").replace("\n", "<br>")
    # 줄바꿈 유지 + HTML 변환
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
    options_html = render_options_section(options)
    
    # 옵션 이미지 생성
    if options_html.strip():
        options_img_path = html_to_png_options(options_html)
        item.options_image_path = options_img_path
        options_section = f"""
        <div style="text-align:center; margin:50px 0;">
            <img src="{options_img_path}" style="max-width:100%; object-fit:contain;">
        </div>
        """
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
    # I) 이미지 절대경로 생성 (Chrome file:/// 전용)
    # ----------------------------------------------------
    PROJECT_DIR = r"C:/soeasy2"
    IMAGES_DIR = os.path.join(PROJECT_DIR, "images")
    IMG_PATH = IMAGES_DIR.replace("\\", "/")    # f-string 안전 버전

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

    WINDLY_TEMP_DIR = os.path.join(os.getcwd(), "windly_temp")
    if not os.path.exists(WINDLY_TEMP_DIR):
        os.makedirs(WINDLY_TEMP_DIR)

    # ★ HTML 경로 windly_temp
    html_path = os.path.join(WINDLY_TEMP_DIR, "options_src.html")

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
      {options_html}
    </body>
    </html>
    """

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    # PNG 덮어쓰기
    png_path = os.path.join(WINDLY_TEMP_DIR, output_name)

    # ★ screenshot 코드 건드리지 않음
    result = {'path': None, 'error': None}

    def worker():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": width, "height": 1200})

                page.goto("file:///" + html_path.replace("\\", "/"))
                page.wait_for_load_state('domcontentloaded')

                body = page.locator("body")
                body.screenshot(path=png_path)

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





def html_to_png_final(html: str, width=720, output_name=None):
    import os, threading, time
    from playwright.sync_api import sync_playwright

    WINDLY_TEMP_DIR = os.path.join(os.getcwd(), "windly_temp")
    if not os.path.exists(WINDLY_TEMP_DIR):
        os.makedirs(WINDLY_TEMP_DIR)

    # ★ HTML을 temp 대신 windly_temp에 저장
    html_path = os.path.join(
        WINDLY_TEMP_DIR,
        f"size_chart_src.html"   # 항상 같은 이름 → 덮어쓰기
    )

    cleaned_html = html.replace('margin-bottom:60px', 'margin-bottom:0px')

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

    # PNG 이름은 고정(덮어쓰기)
    if not output_name:
        output_name = "size_chart.png"

    png_path = os.path.join(WINDLY_TEMP_DIR, output_name)

    # ★ 아래 screenshot 로직은 절대 건드리지 않음
    result = {"path": None, "error": None}

    def worker():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": width, "height": 2000})
                page.goto("file:///" + html_path.replace("\\", "/"))
                page.wait_for_load_state("domcontentloaded")

                table = page.locator("body table")
                table.screenshot(path=png_path)

                browser.close()

            result["path"] = png_path.replace("\\", "/")
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    if result["error"]:
        raise result["error"]

    return result["path"]
