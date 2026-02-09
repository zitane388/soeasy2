# cache_image.py
import requests
from PIL import Image
import io

IMAGE_CACHE = {}   # url → PIL.Image 객체

def get_image_cached(url: str):
    """이미지를 URL 기반으로 캐싱해서 반환(PIL Image)."""
    if url in IMAGE_CACHE:
        return IMAGE_CACHE[url]

    resp = requests.get(url, timeout=5)
    img = Image.open(io.BytesIO(resp.content))
    IMAGE_CACHE[url] = img
    return img
