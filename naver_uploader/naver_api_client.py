# naver_uploader/naver_api_client.py

import time
import json
import requests
import os
import bcrypt
import pybase64


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


class NaverApiClient:
    def __init__(self):
        # 설정 로드
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.client_id = cfg["client_id"]
        self.client_secret = cfg["client_secret"]
        self.seller_id = cfg["seller_id"]

        # 토큰 상태 저장
        self.access_token = None
        self.token_expires_at = 0

    # -------------------------------------------------------------
    # 🔥 테스트에서 성공한 토큰 발급 방식 100% 동일하게 적용
    # -------------------------------------------------------------
    def _get_token(self):
        now = time.time()

        # 기존 토큰 재사용
        if self.access_token and now < self.token_expires_at:
            return self.access_token

        timestamp = str(int(time.time() * 1000))
        raw = f"{self.client_id}_{timestamp}".encode("utf-8")

        hashed = bcrypt.hashpw(raw, self.client_secret.encode("utf-8"))
        signature = pybase64.standard_b64encode(hashed).decode("utf-8")

        url = "https://api.commerce.naver.com/external/v1/oauth2/token"

        data = {
            "client_id": self.client_id,
            "timestamp": timestamp,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": "SELF",
            "sellerId": self.seller_id,
        }

        print("[TOKEN REQ]", data)

        resp = requests.post(url, data=data)

        print("[TOKEN RESP]", resp.status_code, resp.text)

        resp.raise_for_status()
        token_data = resp.json()

        self.access_token = token_data["access_token"]
        self.token_expires_at = now + token_data["expires_in"] - 5

        print("[NaverApiClient] ✔ 토큰 발급 완료")
        return self.access_token

    # -------------------------------------------------------------
    # API 요청
    # -------------------------------------------------------------
    def request(self, method, path, data=None, files=None):
        token = self._get_token()

        # ✔ 테스트에서 성공한 URL 패턴 그대로 사용
        # path 예: "/external/v2/product-images/upload"
        #         "/external/v2/products"
        url = f"https://api.commerce.naver.com{path}"

        print("\n[API] METHOD:", method)
        print("[API] URL:", url)

        headers = {
            "Authorization": f"Bearer {token}"
        }

        if files:
            print("[API] multipart/form-data 요청")
            resp = requests.request(method, url, headers=headers, files=files)
        else:
            headers["Content-Type"] = "application/json"
            print("[API] JSON 요청:", json.dumps(data, indent=2, ensure_ascii=False))
            resp = requests.request(method, url, headers=headers, json=data)

        print("[API RESP]", resp.status_code, resp.text)

        try:
            resp.raise_for_status()
        except Exception as e:
            print("[ERROR] 네이버 API 오류:", resp.text)
            raise e

        return resp.json()

