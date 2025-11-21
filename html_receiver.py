# html_receiver.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

"""
RAW HTML을 확장프로그램으로부터 수신하는 프로그램 전용 HTML Receiver.
- 크롬 확장프로그램 background.js → POST → /receive_html
- scraper.py에서 html_receiver.CAPTURED_HTML 을 조회하여 파싱 실행
"""

# ==========================================================
#  전역 저장 변수 (수신된 HTML을 scraper.py가 읽음)
# ==========================================================
CAPTURED_HTML = None              # 기본
CAPTURED_OPTION_HTML = None       # 옵션
CAPTURED_URL = ""
CAPTURED_OPTION_URL = ""
LENS_PRODUCTS = []

# HTML 저장 디렉토리
CACHE_DIR = "html_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ==========================================================
#  Flask 서버
# ==========================================================
app = Flask(__name__)
CORS(app, supports_credentials=True)


def save_html_to_cache(url: str, html: str) -> str:
    """
    URL → 안전한 파일명으로 변환하여 html_cache/에 저장
    반환값: 저장된 파일의 경로
    """
    import re
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)
    filename = os.path.join(CACHE_DIR, f"{safe}.html")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    return filename

def save_html(url, html):
    import re
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)
    path = os.path.join(CACHE_DIR, f"{safe}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path

# ==========================================================
#  RAW HTML 수신 엔드포인트
# ==========================================================
@app.route("/receive_html_main", methods=["POST"])
def receive_html():
    """
    확장프로그램에서 HTML을 POST로 전송하는 메인 엔드포인트
    """
    global CAPTURED_HTML, CAPTURED_URL, CAPTURED_PRODUCT_NAME

    try:
        data = request.json or {}

        html = data.get("html", "")
        url = data.get("url", "")
        product_name = data.get("product_name", "")

        # 전역단 저장 (scraper.py에서 읽음)
        CAPTURED_HTML = html
        CAPTURED_URL = url
        CAPTURED_PRODUCT_NAME = product_name

        # 파일 저장
        saved_path = save_html_to_cache(url, html)

        print("\n==============================")
        print("📥 RAW HTML RECEIVED")
        print(f"URL: {url}")
        print(f"Product Name: {product_name}")
        print(f"HTML length: {len(html)}")
        print(f"Saved file: {saved_path}")
        print("==============================\n")

        return jsonify({"ok": True, "saved": saved_path})

    except Exception as e:
        print("❌ Error receiving HTML:", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/receive_products_soeasy2", methods=["POST"])
def receive_products_soeasy2():
    """
    Google Lens 확장프로그램에서 수집된 상품 리스트(JSON)를 수신한다.
    HTML이 아니라 JSON 데이터이므로 LENS_PRODUCTS 로 저장.
    """
    global LENS_PRODUCTS
    data = request.json or []

    # 전역 저장
    LENS_PRODUCTS = data

    # JSON을 파일로 저장 (옵션)
    import json
    path = os.path.join(CACHE_DIR, "lens_products_soeasy2.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n==============================")
    print("📥 LENS PRODUCTS RECEIVED")
    print(f"Count: {len(data)}")
    print(f"Saved file: {path}")
    print("==============================\n")

    return jsonify({"ok": True, "count": len(data), "saved": path})


# ==========================================================
#  Health Check
# ==========================================================
@app.route("/", methods=["GET"])
def health():
    return "HTML RECEIVER OK", 200


# ==========================================================
#  서버 종료 엔드포인트
# ==========================================================
@app.route("/shutdown", methods=["POST"])
def shutdown():
    func = request.environ.get("werkzeug.server.shutdown")
    if not func:
        return "Not running with Werkzeug", 500
    func()
    return "HTML Receiver shutting down..."


# ==========================================================
#  main.py에서 thread로 실행될 함수
# ==========================================================
def run_html_receiver():
    """
    GUI 실행 전에 main.py에서 thread로 실행해야 함
    """
    print("📡 HTML Receiver running at http://127.0.0.1:5001")
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,
        use_reloader=False
    )
