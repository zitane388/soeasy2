# widgets/image_loader.py

import requests
from PIL import Image, ImageTk
import io
import base64
import threading

# ==========================================================
# 전역 캐시
# ==========================================================
IMAGE_CACHE = {}      # {(url, size): PhotoImage}
BASE64_CACHE = {}     # {(data, size): PhotoImage}


# ==========================================================
# 내부 유틸: 비율 유지 리사이즈
# ==========================================================
def resize_aspect_fit(img, target_size):
    tw, th = target_size
    iw, ih = img.size

    scale = min(tw / iw, th / ih)
    new_size = (int(iw * scale), int(ih * scale))

    resized = img.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGBA", (tw, th), (255, 255, 255, 0))
    left = (tw - new_size[0]) // 2
    top = (th - new_size[1]) // 2
    canvas.paste(resized, (left, top))

    return canvas


# ==========================================================
# 동기 다운로드 + 캐싱
# ==========================================================
import urllib.request
import ssl
from PIL import Image, ImageTk
import io

from image_tools.image_fetcher import fetch_image_content

def get_cached_image(url, size=(160, 160), disable_cache=False):
    key = (url, size)
    if not disable_cache and key in IMAGE_CACHE:
        return IMAGE_CACHE[key]

    # 통합 다운로더 호출
    data = fetch_image_content(url)
    
    if not data: return None

    try:
        raw_img = Image.open(io.BytesIO(data))
        raw_img.load()
        img = resize_aspect_fit(raw_img, size)
        tki = ImageTk.PhotoImage(img)
        if not disable_cache: IMAGE_CACHE[key] = tki
        return tki
    except: return None




# ==========================================================
# Base64 이미지 (네이버 옵션 이미지 등)
# ==========================================================
def get_cached_image_base64(data, size=(40, 40)):
    key = (data, size)

    if key in BASE64_CACHE:
        return BASE64_CACHE[key]

    try:
        raw = base64.b64decode(data.split(",")[-1])
        raw_img = Image.open(io.BytesIO(raw))
        img = resize_aspect_fit(raw_img, size)
        tki = ImageTk.PhotoImage(img)

        BASE64_CACHE[key] = tki
        return tki

    except Exception:
        return None


# ==========================================================
# 비동기 이미지 로더 (URL)
# ==========================================================
def load_image_async(url, size, callback, root, disable_cache=False):

    # 캐시 즉시 반환
    key = (url, size)
    if not disable_cache and key in IMAGE_CACHE:
        root.after(0, lambda: callback(IMAGE_CACHE[key]))
        return

    def task():
        img = get_cached_image(url, size, disable_cache)
        root.after(0, lambda: callback(img))

    threading.Thread(target=task, daemon=True).start()



# ==========================================================
# 비동기 Base64 로더
# ==========================================================
def load_base64_async(data, size, callback, root):
    def task():
        img = get_cached_image_base64(data, size)
        root.after(0, lambda: callback(img))

    threading.Thread(target=task, daemon=True).start()


# ==========================================================
# 비동기 로컬 파일 이미지 로더
# ==========================================================
def load_local_image_async(path, size, callback, root):
    """
    로컬 파일 경로 → 비동기 리사이즈 → PhotoImage → callback(photo)
    """
    def task():
        try:
            img = Image.open(path)
            img = resize_aspect_fit(img, size)
            tkimg = ImageTk.PhotoImage(img)
            root.after(0, lambda: callback(tkimg))
        except Exception:
            root.after(0, lambda: callback(None))

    threading.Thread(target=task, daemon=True).start()
