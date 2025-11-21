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


def normalize_size_chart(html: str) -> str:
    """원본 HTML의 size table을 번역·정규화해서 반듯한 표로 재구성"""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    if not table:
        return ""

    # ------------------------------------------
    # 1) 테이블 전체 행·열 수집
    # ------------------------------------------
    rows = []
    for tr in table.find_all("tr"):
        cols = tr.find_all(["th", "td"])
        cells = [clean_text(c.get_text(strip=True)) for c in cols]
        if cells:
            rows.append(cells)

    if not rows or len(rows) < 2:
        return ""

    # ------------------------------------------
    # 2) 첫 행 = 헤더 → 매핑 + 번역
    # ------------------------------------------
    raw_header = rows[0]
    translated_header = [translate_header(h) for h in raw_header]

    # ------------------------------------------
    # 3) 표 HTML 재구성
    # ------------------------------------------
    html_rows = []

    # HEADER
    html_rows.append(
        "<tr>" +
        "".join([
            "<th style='border:2px solid #888;padding:10px;"
            "font-size:20px;font-weight:bold;text-align:center;"
            "background:#f5f5f5;'>"
            f"{h}</th>"
            for h in translated_header
        ]) +
        "</tr>"
    )

    # BODY
    for r in rows[1:]:
        html_rows.append(
            "<tr>" +
            "".join([
                "<td style='border:2px solid #ccc;padding:10px;"
                "font-size:18px;text-align:center;'>"
                f"{c}</td>"
                for c in r
            ]) +
            "</tr>"
        )

    # ------------------------------------------
    # 4) 최종 HTML 반환
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


def render_options_section(options):
    """
    options = [{"name":..., "image":...}]
    """
    if not options:
        return ""

    rows = []
    for opt in options:
        image = opt.get("image", "")
        name = opt.get("name", "")

        rows.append(f"""
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tbody>

                <tr>
                    <td style="padding: 10px; text-align: center; width: 100%;">
                        <img src="{image}"
                             style="max-width: 100%; object-fit: contain;">
                    </td>
                </tr>

                <tr style="border-bottom: 3px double;">
                    <td style="text-align: center; padding: 10px;">
                        <strong style="font-size:1.2rem;">{name}</strong>
                    </td>
                </tr>

            </tbody>
        </table>
        """)

    return "\n".join(rows)


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
    name_20 = limit_length(name_40, 20)

    # ----------------------------------------------------
    # C) 상품 이미지
    # ----------------------------------------------------
    images = getattr(item, "images", []) or item.parsed_raw.get("images", [])
    product_images_html = render_product_images(images)

    # ----------------------------------------------------
    # D) 상품설명: 번역 + 요약
    # ----------------------------------------------------
    detail_text = (item.final_description or "").replace("\n", "<br>")
    # 줄바꿈 유지 + HTML 변환
    if detail_text:
        detail_text_html = detail_text.replace("\n", "<br>")
        description_section = f"""
        <div style="text-align:center; line-height:1.7;margin-top:30px;margin-bottom:30px">
            {detail_text_html}
        </div>
        <div style="text-align:center"><br></div>
        <div style="text-align:center"><br></div>
        """
    else:
        description_section = ""

    # ----------------------------------------------------
    # F) 옵션 섹션
    # ----------------------------------------------------
    options = getattr(item, "options", []) or item.parsed_raw.get("colors", [])
    options_section = render_options_section(options)

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
        .replace("{{PRODUCT_IMAGES}}", product_images_html)
        .replace("{{DESCRIPTION_SECTION}}", description_section)
        .replace("{{SIZE_CHART_SECTION}}", size_chart_section)
        .replace("{{OPTIONS_SECTION}}", options_section)
        .replace("{{BOTTOM_IMAGE}}", BOTTOM_IMAGE)
    )

    return final_html.strip()


def html_to_png_final(html: str, width=720, output_name="size_chart.png"):
    """
    HTML 문자열에서 불필요한 마진을 제거하고 <table> 요소만 PNG로 변환합니다.
    """

    temp_dir = tempfile.gettempdir()
    html_path = os.path.join(temp_dir, "size_chart_temp.html")
    png_path = os.path.join(temp_dir, output_name)

    # 1. HTML 문자열에서 문제가 되는 margin-bottom 스타일 제거
    # 'margin-bottom:60px'를 찾아 'margin-bottom:0px'로 변경하거나 아예 제거합니다.
    cleaned_html = html.replace('margin-bottom:60px', 'margin-bottom:0px')
    
    # 2. 전체 HTML 구조 생성
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

    # 3. Playwright 실행
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # 뷰포트 너비만 지정합니다. 높이는 요소 캡처 시 무시됩니다.
        page = browser.new_page(viewport={"width": width, "height": 1000})
        
        page.goto("file:///" + html_path.replace("\\", "/"))

        page.wait_for_load_state('domcontentloaded')

        # 4. <table> 요소만 정확히 타겟팅합니다.
        # 이제 div에 불필요한 마진이 없으므로 깔끔하게 캡처됩니다.
        table_element = page.locator('body > div > table')

        # 스크린샷 캡처
        table_element.screenshot(path=png_path)
        
        browser.close()

    return png_path.replace("\\", "/")



