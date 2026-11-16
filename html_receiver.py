import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from utils.path import p

# ==========================================================
#  전역 저장 변수
# ==========================================================
CAPTURED_HTML = None
CAPTURED_URL = ""
CAPTURED_SITE = ""
CAPTURED_MODE = ""

# HTML 저장 디렉토리 (실행파일 기준)
CACHE_DIR = p("html_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ==========================================================
#  Flask 서버
# ==========================================================
app = Flask(__name__)
CORS(app, supports_credentials=True)


# ------------------ HTML 파일 캐시 저장 ------------------ #
def save_html_to_cache(url: str, html: str) -> str:
    import re
    safe = re.sub(r"[^a-zA-Z0-9]+", "_", url)
    filename = p("html_cache", f"{safe}.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename


# ==========================================================
#  RAW HTML 수신
# ==========================================================
@app.route("/receive_scraped_html", methods=["POST"])
def receive_scraped_html():
    global CAPTURED_HTML, CAPTURED_URL, CAPTURED_SITE, CAPTURED_MODE

    data = request.json or {}

    CAPTURED_HTML = data.get("html", "")
    CAPTURED_URL  = data.get("url", "")
    CAPTURED_SITE = data.get("site", "")
    CAPTURED_MODE = data.get("mode", "")

    saved_path = save_html_to_cache(CAPTURED_URL, CAPTURED_HTML)

    print("\n==============================")
    print("📥 SOEASY2 HTML RECEIVED")
    print(f"URL : {CAPTURED_URL}")
    print(f"SITE: {CAPTURED_SITE}   MODE: {CAPTURED_MODE}")
    print(f"Saved: {saved_path}")
    print("==============================\n")

    return jsonify({"ok": True, "saved": saved_path})


# ==========================================================
#  Health Check
# ==========================================================
@app.route("/", methods=["GET"])
def health():
    return "HTML RECEIVER OK", 200


# ==========================================================
#  서버 종료
# ==========================================================
@app.route("/shutdown", methods=["POST"])
def shutdown():
    func = request.environ.get("werkzeug.server.shutdown")
    if not func:
        return "Not running with Werkzeug", 500
    func()
    return "HTML Receiver shutting down..."


# ==========================================================
#  Thread 엔트리
# ==========================================================
def run_html_receiver():
    print("📡 HTML Receiver running http://127.0.0.1:5001")
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,
        use_reloader=False
    )
