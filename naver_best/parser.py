import ntpath
import logging
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup

# 로거 설정 (기존 설정 유지)
logger = logging.getLogger(__name__)

# [1] 상점 목록 파서 (Selenium page_source용)
def parse_store_html(html_source: str):
    """브라우저 HTML에서 BEST 상품의 이름, 링크, 이미지만 추출"""
    soup = BeautifulSoup(html_source, 'html.parser')
    items = soup.select("li.Hz4XxKbt9h")
    
    rows = []
    for item in items:
        # 1. BEST 뱃지 여부 확인 (뱃지가 없으면 수집 대상에서 제외)
        best_badge = item.select_one("em.zxCBgkZWCG")
        is_best = (best_badge and "BEST" in best_badge.get_text().upper())

        if not is_best:
            continue

        # 2. 상품명 추출
        name_tag = item.select_one("strong.oFvW5kJSyb")
        name = name_tag.get_text(strip=True) if name_tag else ""
        
        # 3. 상품 ID 및 링크 추출
        data_node = item.select_one("[data-shp-contents-id]")
        pid = (data_node.get("data-shp-contents-id") or "").strip() if data_node else ""
        
        link_tag = item.select_one("a.linkAnchor")
        href = link_tag['href'] if link_tag else f"/products/{pid}"

        # 4. 이미지 추출 (고화질 변환)
        img_tag = item.select_one("img.eGeLGHztiu")
        if img_tag:
            img_base = img_tag['src'].split('?')[0]
            img = f"{img_base}?type=w1100"
        else:
            img = ""

        # 5. 필요한 정보만 구성하여 추가
        if name:
            rows.append({
                "name": name,
                "href": href,
                "img": img
            })
            
    return rows

# ───────────────────────────────────────────────
# [2] 상세페이지 MHTML 파서 (이미지, 설명, 옵션)
# ───────────────────────────────────────────────
def parse_detail_html(html: str):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. 상품명 추출
    name_tag = soup.select_one("h3._copyable")
    product_name = name_tag.get_text(strip=True) if name_tag else "상품명 없음"
    
    # 2. 상품 이미지 추출 (고화질 변환 포함)
    image_tags = soup.select("ul.R0_zGxkF9z img.fxmqPhYp6y")
    images = []
    for img in image_tags:
        if img.has_attr('src'):
            img_base = img['src'].split('?')[0]
            images.append(f"{img_base}?type=w1100")
    
    # 3. 상세 설명 텍스트 추출 (SmartEditor ONE 전용)
    container = soup.select_one(".se-main-container")
    full_description = ""
    if container:
        text_elements = container.select(".se-text-paragraph")
        extracted_text = [el.get_text(strip=True) for el in text_elements if el.get_text(strip=True)]
        full_description = "\n".join(extracted_text)
    
    # 4. 옵션 데이터 추출
    options_data = []
    # 현재 펼쳐져 있는(aria-expanded="true") 옵션의 이름을 가져옵니다.
    current_group = soup.select_one("div.KobocOawE2 a._yGBCMWCWu[aria-expanded='true']")
    group_name = current_group.get_text(strip=True) if current_group else "옵션"

    # 현재 화면에 떠 있는 리스트박스 아이템들을 추출
    ul = soup.select_one("ul[role='listbox']")
    if ul:
        items = [li.get_text(strip=True) for li in ul.select("li.OoSVzcevbO") if li.get_text(strip=True)]
        if items:
            options_data.append({
                "group": group_name,
                "items": items
            })
            
    return images, full_description, options_data, product_name