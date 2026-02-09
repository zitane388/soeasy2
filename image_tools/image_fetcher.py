import httpx
import requests
import time
import re
from config.image_settings import HTTP2_REQUIRED_DOMAINS, COMMON_IMAGE_HEADERS

# MUJI 전용 HTTP/2 클라이언트
_HTTP2_CLIENT = httpx.Client(
    http2=True, 
    headers=COMMON_IMAGE_HEADERS, 
    timeout=15.0,
    follow_redirects=True
)

def simplify_muji_url(url):
    """
    www.muji.com의 복잡한 경로를 img.muji.net의 단순 구조로 변경합니다.
    변경 전: https://www.muji.com/public/media/img/item/4547315778225_org.jpg
    변경 후: https://img.muji.net/img/item/4547315778225_org.jpg (혹은 규격에 맞게 치환)
    """
    if "muji.com" in url:
        # 파일명 부분만 추출 (예: 4547315778225_org.jpg)
        filename = url.split('/')[-1]
        
        # 만약 원본 파일명이 _org(오리지널)라면, 
        # 이미지 서버 표준인 _400 이나 _1260 없이도 접근 가능한지 확인 후 리턴
        return f"https://img.muji.net/img/item/{filename}"
    
    return url

def fetch_image_content(url, max_retries=3):
    # 1. 주소 단순화 시도
    target_url = simplify_muji_url(url)
    
    # 2. MUJI 여부 확인 (is_http2_target 활용)
    is_http2_target = any(domain in target_url for domain in HTTP2_REQUIRED_DOMAINS)
    
    for attempt in range(max_retries):
        try:
            if is_http2_target:
                # [Case A] 단순화된 주소로 HTTP/2 요청
                resp = _HTTP2_CLIENT.get(target_url)
                
                # 만약 단순화된 주소(_org 등)가 404라면, 원본 주소로 한 번 더 시도
                if resp.status_code != 200 and target_url != url:
                    resp = _HTTP2_CLIENT.get(url)
                
                resp.raise_for_status()
                return resp.content
            else:
                # [Case B] 일반 사이트
                resp = requests.get(target_url, headers=COMMON_IMAGE_HEADERS, timeout=10)
                resp.raise_for_status()
                return resp.content
                
        except Exception as e:
            print(f"[IMAGE_FETCHER] {attempt+1}차 실패: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
                
    return None

import hashlib

def get_unique_images_by_content(image_urls, fetcher_func):
    """
    이미지를 실제로 다운로드하여 내용(Hash)이 중복되는지 체크합니다.
    """
    seen_hashes = set()
    unique_urls = []

    print(f"[CLEANER] 중복 검사 시작 (총 {len(image_urls)}개)...")

    for url in image_urls:
        content = fetcher_func(url) # 이미 만든 fetch_image_content 사용
        if not content:
            continue

        # 이미지 내용으로 고유한 지문(MD5) 생성
        img_hash = hashlib.md5(content).hexdigest()

        if img_hash not in seen_hashes:
            unique_urls.append(url)
            seen_hashes.add(img_hash)
        else:
            print(f"[CLEANER] 중복 이미지 제외: {url.split('/')[-1]}")

    return unique_urls