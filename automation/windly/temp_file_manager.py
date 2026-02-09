import os
import requests
import io
from PIL import Image
from image_tools.image_fetcher import fetch_image_content

MAX_WINDLY_MB = 5
MAX_BYTES = MAX_WINDLY_MB * 1024 * 1024
MAX_EDGE = 1600
JPEG_QUALITY_START = 85
JPEG_QUALITY_MIN = 60


def make_windly_safe_image(src_path: str, out_path: str) -> str:
    img = Image.open(src_path).convert("RGB")

    # 해상도 제한
    w, h = img.size
    scale = min(1.0, MAX_EDGE / max(w, h))
    if scale < 1.0:
        img = img.resize(
            (int(w * scale), int(h * scale)),
            Image.LANCZOS
        )

    quality = JPEG_QUALITY_START
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=quality, optimize=True)
        size = buf.tell()

        if size <= MAX_BYTES or quality <= JPEG_QUALITY_MIN:
            with open(out_path, "wb") as f:
                f.write(buf.getvalue())
            break

        quality -= 5

    return out_path


def download_temp_images(urls, windly_temp_path):
    os.makedirs(windly_temp_path, exist_ok=True)
    files = []
    for idx, url in enumerate(urls):
        content = fetch_image_content(url) # 통합 다운로더 사용
        if not content: continue
        
        raw_path = os.path.join(windly_temp_path, f"{idx:03d}_raw.jpg")
        with open(raw_path, "wb") as f:
            f.write(content)

        # -------------------------
        # 2) Windly 안전 이미지 생성
        # -------------------------
        safe_name = f"{idx:03d}_windly.jpg"
        safe_path = os.path.join(windly_temp_path, safe_name)

        make_windly_safe_image(raw_path, safe_path)

        size_mb = os.path.getsize(safe_path) / (1024 * 1024)
        print(f"[WINDLY IMG] {safe_name} = {size_mb:.2f}MB")

        # -------------------------
        # 3) 입력 순서 그대로 append
        # -------------------------
        files.append(safe_path)

    return files


def cleanup_windly_temp(windly_temp_path):
    try:
        for name in os.listdir(windly_temp_path):
            path = os.path.join(windly_temp_path, name)
            if os.path.isfile(path):
                os.remove(path)
    except Exception as e:
        print(f"[WARN] windly_temp 정리 오류: {e}")
