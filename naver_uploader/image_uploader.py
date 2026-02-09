# naver_uploader/image_uploader.py

import requests
import time, os, io
from naver_uploader.naver_api_client import NaverApiClient
from image_tools.image_fetcher import fetch_image_content
from utils.path import p
from PIL import Image


class ImageUploader:
    """
    이미지 URL → 네이버 스마트스토어 CDN 업로드
    구매대행은 반드시 EXTERNAL v1 이미지 업로드 API 사용
    """

    def __init__(self):
        self.api = NaverApiClient()

    # =========================================================
    # 🔥 네이버 업로드 전 필수 정규화 (핵심)
    # =========================================================
    def _normalize_bytes_for_naver(self, img_bytes: bytes) -> bytes:
        img = Image.open(io.BytesIO(img_bytes))

        # 알파 제거 + RGB 강제
        if img.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = bg
        else:
            img = img.convert("RGB")

        out = io.BytesIO()
        img.save(out, format="JPEG", quality=95, subsampling=0)
        return out.getvalue()

    # =========================================================
    # URL 업로드
    # =========================================================
    def upload_image_from_url(self, url: str, max_retry=5):

        img_bytes = fetch_image_content(url)
        if not img_bytes:
            return None

        # 🔥 정규화 적용
        img_bytes = self._normalize_bytes_for_naver(img_bytes)

        token = self.api._get_token()
        upload_url = "https://api.commerce.naver.com/external/v1/product-images/upload"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;charset=UTF-8"
        }

        files = {
            "imageFiles": ("image.jpg", img_bytes, "image/jpeg")
        }

        for retry in range(max_retry):
            try:
                print("\n[UPLOAD] 이미지 업로드 요청")

                r = requests.post(upload_url, headers=headers, files=files)
                print("[UPLOAD RESP]", r.status_code, r.text)

                if r.status_code == 429:
                    wait = (retry + 1) * 1.2
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                return r.json()["images"][0]["url"]

            except Exception as e:
                print("[IMG] 네이버 API 업로드 실패:", e)
                return None

        return None

    # =========================================================
    # 파일 업로드
    # =========================================================
    def upload_image_from_file(self, file_path: str, max_retry=5):

        if file_path and not os.path.isabs(file_path):
            file_path = p(file_path)

        if not file_path or not os.path.exists(file_path):
            print(f"[IMG] 로컬 이미지 없음: {file_path}")
            return None

        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            print(f"[IMG] 파일 읽기 실패: {e}")
            return None

        # 🔥 정규화 적용
        img_bytes = self._normalize_bytes_for_naver(img_bytes)

        token = self.api._get_token()
        upload_url = "https://api.commerce.naver.com/external/v1/product-images/upload"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json;charset=UTF-8"
        }

        files = {
            "imageFiles": ("image.jpg", img_bytes, "image/jpeg")
        }

        for retry in range(max_retry):
            try:
                print("\n[UPLOAD] 로컬 이미지 업로드 요청")

                r = requests.post(upload_url, headers=headers, files=files)
                print("[UPLOAD RESP]", r.status_code, r.text)

                if r.status_code == 429:
                    wait = (retry + 1) * 1.2
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                return r.json()["images"][0]["url"]

            except Exception as e:
                print("[IMG] 업로드 실패:", e)
                return None

        return None
