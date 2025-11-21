# naver_uploader/image_uploader.py

import requests
from .naver_api_client import NaverApiClient


class ImageUploader:
    """
    이미지 URL → 네이버 스마트스토어 CDN 업로드
    """

    def __init__(self):
        self.api = NaverApiClient()

    def upload_image_from_url(self, url: str):
        """
        외부 이미지 URL을 스마트스토어 이미지 서버로 업로드
        """

        # ---------------------------------------------------------
        # 1) 이미지 다운로드
        # ---------------------------------------------------------
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            img_bytes = resp.content
        except Exception as e:
            print(f"[IMG] 이미지 다운로드 실패: {url} → {e}")
            return None

        # ---------------------------------------------------------
        # 2) 네이버 명세에 맞는 multipart 업로드
        # ---------------------------------------------------------
        files = {
            # 🔥 네이버는 반드시 imageFiles 라는 키로 받아야 함
            "imageFiles": ("image.jpg", img_bytes, "image/jpeg")
        }

        try:
            result = self.api.request(
                method="POST",
                path="/product-images/upload",  # external/v1/product-images/upload
                files=files,
                data=None
            )

        except Exception as e:
            print("[IMG] 네이버 API 업로드 실패:", e)
            return None

        # ---------------------------------------------------------
        # 3) 반환값 파싱
        # ---------------------------------------------------------
        try:
            return result["images"][0]["url"]
        except Exception:
            print("[IMG] 업로드 응답 파싱 실패:", result)
            return None
