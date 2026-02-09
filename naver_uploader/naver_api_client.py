import time
import json
import requests
import os
import threading
import bcrypt
print("bcrypt module path =", bcrypt.__file__)
print("bcrypt version =", bcrypt.__version__)
import pybase64

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

class NaverApiClient:
    def __init__(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.client_id = cfg["client_id"]
        self.client_secret = cfg["client_secret"]
        self.seller_id = cfg["seller_id"]

        self.access_token = None
        self.token_expires_at = 0
        
        self._token_lock = threading.Lock()

    def _get_token(self):
        with self._token_lock:
            now = time.time()

            if self.access_token and now < self.token_expires_at:
                return self.access_token

            timestamp = str(int(time.time() * 1000))
            raw = f"{self.client_id}_{timestamp}".encode("utf-8")

            hashed = bcrypt.hashpw(raw, self.client_secret.encode("utf-8"))
            signature = pybase64.b64encode(hashed).decode("utf-8")

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
            self.token_expires_at = now + token_data["expires_in"] - 10

            print("[NaverApiClient] ✔ 토큰 발급 완료")
            return self.access_token

    def request(self, method, path, data=None, files=None):
        token = self._get_token()

        url = f"https://api.commerce.naver.com{path}"

        print("\n[API] METHOD:", method)
        print("[API] URL:", url)

        headers = {
            "Authorization": f"Bearer {token}"
        }

        if files:
            resp = requests.request(method, url, headers=headers, files=files)
        else:
            headers["Content-Type"] = "application/json"
            print("[API] JSON 요청:", json.dumps(data, indent=2, ensure_ascii=False))
            resp = requests.request(method, url, headers=headers, json=data)

        print("[API RESP]", resp.status_code, resp.text)

        try:
            resp.raise_for_status()
        except Exception as e:
            print("\n================ NAVER API ERROR ================\n")
            print("URL:", url)
            print("METHOD:", method)
            print("STATUS:", resp.status_code)
            print("RESPONSE TEXT:", resp.text)
            print("REQUEST BODY:", data)
            print("\n==================================================\n")
            raise

        return resp.json()
