import cv2
import numpy as np
import easyocr
import PIL.Image
from rembg import remove
from app_startup import SESSION
from image_tools.logo.logo_job import LogoJob

# ======================================================
# OCR Reader (전역 1회 생성)
# ======================================================
print("[LOGO][INIT] Initializing OCR Reader")
_OCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)

# ======================================================
# 1. BiRefNet 보호 마스크
# ======================================================
def get_fg_mask(img_rgb: np.ndarray) -> np.ndarray:
    print(f"[LOGO][MASK] get_fg_mask start shape={img_rgb.shape}")
    pil = PIL.Image.fromarray(img_rgb)
    m = remove(pil, session=SESSION, only_mask=True)
    m = np.array(m)

    if m.ndim == 3:
        m = m[:, :, -1]

    mask = np.where(m > 128, 255, 0).astype(np.uint8)
    print(
        "[LOGO][MASK] fg_mask generated "
        f"fg_ratio={np.sum(mask > 0) / mask.size:.3f}"
    )
    return mask

# ======================================================
# 2. OCR 텍스트 점수
# ======================================================
def score_text(img_rgb):
    print("[LOGO][OCR] score_text start")
    try:
        for (_, text, conf) in _OCR_READER.readtext(img_rgb):
            print(f"[LOGO][OCR] detected text='{text}' conf={conf:.3f}")
            if conf > 0.3:
                print("[LOGO][OCR] HIT → +3")
                return 3
    except Exception as e:
        print("[LOGO][OCR][ERROR]", repr(e))

    print("[LOGO][OCR] no valid text → +0")
    return 0

# ======================================================
# 3. 타일 기반 엣지 밀도
# ======================================================
def score_edge_density(img_rgb, bg_mask):
    print("[LOGO][EDGE] score_edge_density start")

    gray = cv2.GaussianBlur(
        cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY), (5, 5), 0
    )
    edges = cv2.Canny(gray, 120, 240)

    h, w = img_rgb.shape[:2]
    win, stride = 96, 48
    max_density = 0.0

    for y in range(0, h - win, stride):
        for x in range(0, w - win, stride):
            bm = bg_mask[y:y+win, x:x+win]
            if np.sum(bm) < win * win * 0.7:
                continue

            density = np.sum(edges[y:y+win, x:x+win] & bm > 0) / np.sum(bm)
            max_density = max(max_density, density)

            if density > 0.015:
                print(f"[LOGO][EDGE] HIT density={density:.5f} → +2")
                return 2

    print(f"[LOGO][EDGE] max_density={max_density:.5f} → +0")
    return 0

# ======================================================
# 4. 타일 기반 고채도 평탄 영역
# ======================================================
def score_color_flatness(img_rgb, bg_mask):
    print("[LOGO][COLOR] score_color_flatness start")

    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
    sat, val = hsv[:, :, 1], hsv[:, :, 2]

    h, w = img_rgb.shape[:2]
    win, stride = 96, 48
    max_ratio = 0.0

    for y in range(0, h - win, stride):
        for x in range(0, w - win, stride):
            bm = bg_mask[y:y+win, x:x+win]
            if np.sum(bm) < win * win * 0.7:
                continue

            mask = bm & (sat[y:y+win, x:x+win] > 110) & (val[y:y+win, x:x+win] > 130)
            ratio = np.sum(mask) / np.sum(bm)
            max_ratio = max(max_ratio, ratio)

            if ratio > 0.010:
                print(f"[LOGO][COLOR] HIT ratio={ratio:.5f} → +2")
                return 2

    print(f"[LOGO][COLOR] max_ratio={max_ratio:.5f} → +0")
    return 0

# ======================================================
# 5. 단일 이미지 분석
# ======================================================
def analyze_logo_image(img_rgb: np.ndarray) -> dict:
    print("[LOGO][ANALYZE] start")

    fg_mask = get_fg_mask(img_rgb)
    bg_mask = cv2.dilate(fg_mask, np.ones((15, 15), np.uint8)) == 0

    t = score_text(img_rgb)
    e = score_edge_density(img_rgb, bg_mask)
    c = score_color_flatness(img_rgb, bg_mask)

    score = t + e + c
    need_remove = score >= 3

    print(
        "[LOGO][ANALYZE] result "
        f"text={t}, edge={e}, color={c}, total={score}, "
        f"need_remove={need_remove}"
    )

    return {
        "need_remove": need_remove,
        "score": score,
        "detail": {
            "text": t,
            "edge": e,
            "color": c,
        }
    }

# ======================================================
# 6. 상품 전체 이미지 처리 (메모리 ONLY)
# ======================================================
def process_logo_images_for_item(job: LogoJob) -> list:
    """
    메모리 분석 단계
    """
    from image_tools.thumbnail_runner import _download_image_to_temp

    # ✅ 여기서만 image_urls 결정
    image_urls = job.image_urls or []

    print(
        f"[LOGO][ITEM] process start item_id={job.item.item_id} "
        f"image_count={len(image_urls)}"
    )

    results = []

    for idx, url in enumerate(image_urls):
        print(f"\n[LOGO][ITEM] IMAGE idx={idx} url={url}")

        try:
            src_path = _download_image_to_temp(url)

            img_bgr = cv2.imread(src_path)
            if img_bgr is None:
                raise RuntimeError("cv2.imread failed")

            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

            analysis = analyze_logo_image(img_rgb)
            need_remove = analysis["need_remove"]

            if need_remove:
                # 1. rembg 실행 (RGBA 결과)
                removed = remove(
                    PIL.Image.fromarray(img_rgb),
                    session=SESSION
                ).convert("RGBA")

                # 2. 알파 채널만 추출
                alpha = np.array(removed)[:, :, 3]

                # 3. 원본 RGB + 알파 재합성 (⭐ 핵심)
                rgba = np.dstack([img_rgb, alpha])

                img_no_bg = PIL.Image.fromarray(rgba, "RGBA")
            else:
                img_no_bg = None


            results.append({
                "index": idx,
                "url": url,
                "need_remove": need_remove,
                "image": img_no_bg,
                "file_path": None,
                "analysis": analysis,
            })

        except Exception as e:
            results.append({
                "index": idx,
                "url": url,
                "need_remove": False,
                "image": None,
                "file_path": None,
                "error": str(e),
            })

    print(
        f"\n[LOGO][ITEM] DONE item_id={job.item.item_id} "
        f"processed={len(results)}"
    )

    return results

