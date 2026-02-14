import os
import requests
import io
import hashlib
from PIL import Image, ImageDraw
from PIL import Image
from image_tools.image_fetcher import fetch_image_content

MAX_WINDLY_MB = 5
MAX_BYTES = MAX_WINDLY_MB * 1024 * 1024
MAX_EDGE = 1600
JPEG_QUALITY_START = 85
JPEG_QUALITY_MIN = 60


def make_windly_safe_image(src_path: str, out_path: str) -> str:
    debug_bg = os.environ.get("WINDLY_DEBUG_BG") == "1"
    img_src = Image.open(src_path)
    if debug_bg:
        try:
            dbg_dir = os.path.join(os.path.dirname(out_path), "bg_debug")
            os.makedirs(dbg_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(out_path))[0]
            pre_path = os.path.join(dbg_dir, f"{base}__pre.png")
            img_src.save(pre_path)
            print(f"[WINDLY IMG][BG] saved pre-bg -> {pre_path}")
        except Exception as e:
            print(f"[WINDLY IMG][BG][WARN] pre save failed: {e}")

    img = img_src.convert("RGB")

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

    if debug_bg:
        try:
            dbg_dir = os.path.join(os.path.dirname(out_path), "bg_debug")
            os.makedirs(dbg_dir, exist_ok=True)
            base = os.path.splitext(os.path.basename(out_path))[0]
            post_path = os.path.join(dbg_dir, f"{base}__post.png")
            img.save(post_path)
            print(f"[WINDLY IMG][BG] saved post-bg -> {post_path}")
        except Exception as e:
            print(f"[WINDLY IMG][BG][WARN] post save failed: {e}")

    # 간단 해시 로그 (디버깅용)
    try:
        with open(out_path, "rb") as f:
            md5 = hashlib.md5(f.read()).hexdigest()
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        print(f"[WINDLY IMG][LOCAL] out={os.path.basename(out_path)} size={size_mb:.2f}MB md5={md5}")
    except Exception as e:
        print(f"[WINDLY IMG][LOCAL][WARN] hash failed: {e}")

    return out_path


def make_windly_safe_copy_from_local(src_path: str, out_path: str) -> str:
    """
    로컬 파일을 Windly 업로드 규격(JPEG/1600px/용량 제한)에 맞게 변환
    """
    # 디버깅용 마킹(필요 시): WINDLY_DEBUG_MARK=1
    mark = os.environ.get("WINDLY_DEBUG_MARK") == "1"
    if mark:
        try:
            img = Image.open(src_path).convert("RGB")
            w, h = img.size
            draw = ImageDraw.Draw(img)
            draw.rectangle([w - 6, h - 6, w - 1, h - 1], fill=(255, 0, 0))
            temp_marked = out_path + ".marked.jpg"
            img.save(temp_marked, format="JPEG", quality=95)
            return make_windly_safe_image(temp_marked, out_path)
        except Exception as e:
            print(f"[WINDLY IMG][LOCAL][WARN] mark failed: {e}")

    return make_windly_safe_image(src_path, out_path)


def download_temp_images(urls, windly_temp_path):
    os.makedirs(windly_temp_path, exist_ok=True)
    files = []
    url_to_file = {}
    for idx, url in enumerate(urls):
        print(f"[WINDLY IMG] download src[{idx}] = {url}")
        content = fetch_image_content(url) # 통합 다운로더 사용
        if not content: continue
        
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        raw_path = os.path.join(windly_temp_path, f"{idx:03d}_{url_hash}_raw.jpg")
        with open(raw_path, "wb") as f:
            f.write(content)

        # -------------------------
        # 2) Windly 안전 이미지 생성
        # -------------------------
        safe_name = f"{idx:03d}_{url_hash}_windly.jpg"
        safe_path = os.path.join(windly_temp_path, safe_name)

        make_windly_safe_image(raw_path, safe_path)

        size_mb = os.path.getsize(safe_path) / (1024 * 1024)
        print(f"[WINDLY IMG] {safe_name} = {size_mb:.2f}MB")

        # -------------------------
        # 3) 입력 순서 그대로 append
        # -------------------------
        files.append(safe_path)
        url_to_file[url] = safe_path
        print(f"[WINDLY IMG] saved -> {safe_path}")

    return files, url_to_file


def cleanup_windly_temp(windly_temp_path):
    try:
        for name in os.listdir(windly_temp_path):
            path = os.path.join(windly_temp_path, name)
            if os.path.isfile(path):
                os.remove(path)
    except Exception as e:
        print(f"[WARN] windly_temp 정리 오류: {e}")
