import threading
import io
from PIL import Image, ImageTk, ImageOps
# 🔥 우리가 만든 고성능 로더 임포트
from image_tools.image_fetcher import fetch_image_content

# 전역 캐시
_THUMB_CACHE = {}      # { (url, size): PhotoImage }
_THUMB_RAW_CACHE = {}  # { url: PIL.Image }

# ------------------------------------------------------------
# 내부: URL → PIL.Image 로드 (수정됨)
# ------------------------------------------------------------
def _load_image_from_url(url):
    if url in _THUMB_RAW_CACHE:
        return _THUMB_RAW_CACHE[url]

    try:
        # 🔥 urllib 대신 fetch_image_content 사용 (HTTP/2 및 MUJI 대응)
        data = fetch_image_content(url)
        if not data:
            return None
            
        img = Image.open(io.BytesIO(data))
        
        # RGBA나 P 모드일 경우 패딩(white) 적용을 위해 RGB로 변환
        if img.mode != "RGB":
            img = img.convert("RGB")
            
        _THUMB_RAW_CACHE[url] = img
        return img
    except Exception as e:
        print(f"[THUMB_HELPER] 이미지 로드 실패: {e}")
        return None

# ------------------------------------------------------------
# PIL.Image → 정사각형 썸네일(Padded) - 기존과 동일
# ------------------------------------------------------------
def make_square_thumbnail(img, size=(60, 60), pad_color="white"):
    try:
        img_copy = img.copy()
        img_copy.thumbnail(size)
        padded = ImageOps.pad(img_copy, size, color=pad_color)
        return padded
    except:
        return None

# ------------------------------------------------------------
# 비동기 썸네일 생성 - 기존과 동일하나 내부적으로 위 수정된 함수 호출
# ------------------------------------------------------------
def load_thumbnail_async(url, size, callback, root, pad_color="white"):
    key = (url, size)

    if key in _THUMB_CACHE:
        # 캐시가 있어도 PhotoImage 객체가 유효한지 확인 (가끔 GC됨)
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