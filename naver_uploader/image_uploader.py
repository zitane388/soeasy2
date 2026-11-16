# naver_uploader/image_uploader.py

import requests
import time, os
from naver_uploader.naver_api_client import NaverApiClient
from image_tools.image_fetcher import fetch_image_content
from utils.path import p 

class ImageUploader:
    """
    이미지 URL → 네이버 스마트스토어 CDN 업로드
    구매대행은 반드시 EXTERNAL v1 이미지 업로드 API 사용해야 함.
    """

    def __init__(self):
        self.api = NaverApiClient()

    def upload_image_from_url(self, url: str, max_retry=5):
        """
        외부 이미지 URL을 스마트스토어 이미지 서버로 업로드
        """

        # 1) 이미지 다운로드
        img_bytes = fetch_image_content(url)
        if not img_bytes:
            return None

        # 2) 업로드용 토큰 발급
        token = self.api._get_token()

        upload_url = "https://api.commerce.naver.com/external/v1/product-images/upload"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;charset=UTF-8"
        }

        files = {
            "imageFiles": ("image.jpg", img_bytes, "image/jpeg")
        }

        # 3) 직접 요청(중요!) + 429 재시도 추가
        for retry in range(max_retry):
            try:
                print("\n[UPLOAD] 이미지 업로드 요청 → external/v1/product-images/upload")

                r = requests.post(upload_url, headers=headers, files=files)
                print("[UPLOAD RESP]", r.status_code, r.text)

                # 429 handling
                if r.status_code == 429:
                    wait = (retry + 1) * 1.2
                    print(f"[UPLOAD 429] Too Many Requests → {wait:.1f}초 대기 후 재시도...")
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                return r.json()["images"][0]["url"]

            except Exception as e:
                # 429는 위에서 처리했으므로 여기서는 기타 에러만 처리
                print("[IMG] 네이버 API 업로드 실패:", e)
                return None

        print("[IMG] 업로드 실패 (429 반복)")
        return None


    def upload_image_from_file(self, file_path: str, max_retry=5):
        """
        로컬 이미지 파일 → 스마트스토어 CDN 업로드
        (make_thumbnail_img 용)
        """

        # ⬅️ 상대경로면 exe 기준 절대경로로 변환
        if file_path and not os.path.isabs(file_path):
            file_path = p(file_path)

        if not file_path or not os.path.exists(file_path):
            print(f"[IMG] 로컬 이미지 없음: {file_path}")
            return None

        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            print(f"[IMG] 로컬 이미지 읽기 실패: {file_path} → {e}")
            return None

        token = self.api._get_token()
        upload_url = "https://api.commerce.naver.com/external/v1/product-images/upload"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;charset=UTF-8"
        }

        files = {
            "imageFiles": ("image.png", img_bytes, "image/png")
        }

        for retry in range(max_retry):
            try:
                print("\n[UPLOAD] 로컬 이미지 업로드 요청")

                r = requests.post(upload_url, headers=headers, files=files)
                print("[UPLOAD RESP]", r.status_code, r.text)

                if r.status_code == 429:
                    wait = (retry + 1) * 1.2
                    print(f"[UPLOAD 429] {wait:.1f}초 대기 후 재시도")
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                return r.json()["images"][0]["url"]

            except Exception as e:
                print("[IMG] 로컬 이미지 업로드 실패:", e)
                return None

        return None
