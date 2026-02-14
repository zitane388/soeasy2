import io
import os
import threading

import requests
from PIL import Image, ImageOps, ImageTk

from image_tools.image_fetcher import fetch_image_content

_THUMB_CACHE = {}      # {(url, size): PhotoImage}
_THUMB_RAW_CACHE = {}  # {url: PIL.Image}


def _decode_image_bytes(data: bytes):
    img = Image.open(io.BytesIO(data))
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _load_image_from_url(url):
    if isinstance(url, str) and os.path.exists(url):
        try:
            img = Image.open(url)
            img.load()
            if img.mode != "RGB":
                img = img.convert("RGB")
            return img
        except Exception as e:
            print(f"[THUMB_HELPER] local image load failed: {e}")
            return None

    if url in _THUMB_RAW_CACHE:
        return _THUMB_RAW_CACHE[url]

    # primary path
    try:
        data = fetch_image_content(url)
        if data:
            img = _decode_image_bytes(data)
            _THUMB_RAW_CACHE[url] = img
            return img
    except Exception as e:
        primary_error = e
    else:
        primary_error = Exception("empty image bytes")

    # fallback path
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.supersports.com/ja-jp/",
            "Accept": "image/jpeg,image/png,image/*;q=0.8,*/*;q=0.5",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        img = _decode_image_bytes(resp.content)
        _THUMB_RAW_CACHE[url] = img
        return img
    except Exception as fallback_error:
        print(
            "[THUMB_HELPER] image load failed:",
            primary_error,
            "/ fallback:",
            fallback_error,
        )
        return None


def make_square_thumbnail(img, size=(60, 60), pad_color="white"):
    try:
        img_copy = img.copy()
        img_copy.thumbnail(size)
        return ImageOps.pad(img_copy, size, color=pad_color)
    except Exception:
        return None


def load_thumbnail_async(url, size, callback, root, pad_color="white"):
    key = (url, size)

    if key in _THUMB_CACHE:
        root.after(0, lambda: callback(_THUMB_CACHE[key]))
        return

    def task():
        img = _load_image_from_url(url)
        if img is None:
            root.after(0, lambda: callback(None))
            return

        thumb = make_square_thumbnail(img, size, pad_color)
        if thumb is None:
            root.after(0, lambda: callback(None))
            return

        photo = ImageTk.PhotoImage(thumb)
        _THUMB_CACHE[key] = photo
        root.after(0, lambda: callback(photo))

    threading.Thread(target=task, daemon=True).start()


def clear_thumbnail_cache():
    _THUMB_CACHE.clear()
    _THUMB_RAW_CACHE.clear()

