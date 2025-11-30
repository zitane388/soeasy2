# naver_uploader/image_uploader.py

import requests
import time
import json
import bcrypt
import pybase64
from naver_uploader.naver_api_client import NaverApiClient

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
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img_bytes = resp.content
        except Exception as e:
            print(f"[IMG] 이미지 다운로드 실패: {url} → {e}")
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
