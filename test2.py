import os
import cv2
import numpy as np
import easyocr
from rembg import remove
from app_startup import SESSION
import PIL.Image

# ======================================================
# 1. 이미지 로드
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(BASE_DIR, "test1.jpg")

img_bgr = cv2.imread(IMG_PATH)
if img_bgr is None:
    raise FileNotFoundError("이미지 로드 실패")

img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
h, w = img_rgb.shape[:2]

# ======================================================
# 2. BiRefNet 보호 마스크 (인물/상품)
# ======================================================
def get_fg_mask(img):
    pil = PIL.Image.fromarray(img)
    m = remove(pil, session=SESSION, only_mask=True)
    m = np.array(m)
    if m.ndim == 3:
        m = m[:, :, -1]
    return np.where(m > 128, 255, 0).astype(np.uint8)

fg_mask = get_fg_mask(img_rgb)

# 🔥 경계 완충 (가짜 엣지 차단 핵심)
fg_safe = cv2.dilate(fg_mask, np.ones((15, 15), np.uint8))
bg_mask = fg_safe == 0

# ======================================================
# 3. OCR 텍스트 로고 점수 (작은 텍스트 대응)
# ======================================================
def score_text(img):
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    res = reader.readtext(img)

    for (_, text, conf) in res:
        if conf > 0.3:
            return 3, f"OCR 감지(text='{text}', conf={conf:.2f})"

    return 0, "OCR 감지 없음"

# ======================================================
# 4. 타일 기반 엣지 밀도 (노이즈 차단 버전)
# ======================================================
def score_edge_density(img, bg_mask):
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # 🔥 노이즈 제거
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 🔥 threshold 상향 (가짜 엣지 제거)
    edges = cv2.Canny(gray, 120, 240)

    win = 96
    stride = 48

    max_density = 0.0
    hit = False

    for y in range(0, h - win, stride):
        for x in range(0, w - win, stride):
            bm = bg_mask[y:y+win, x:x+win]
            if np.sum(bm) < win * win * 0.7:
                continue

            em = edges[y:y+win, x:x+win] & bm
            density = np.sum(em > 0) / np.sum(bm)
            max_density = max(max_density, density)

            if density > 0.015:   # ★ 안정 임계
                hit = True

    if hit:
        return 2, f"국소 엣지 밀도 높음(max_density={max_density:.4f})"
    return 0, f"엣지 밀도 낮음(max_density={max_density:.4f})"

# ======================================================
# 5. 타일 기반 고채도 평탄 영역 (소형 심볼 대응)
# ======================================================
def score_color_flatness(img, bg_mask):
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]

    win = 96
    stride = 48

    max_ratio = 0.0
    hit = False

    for y in range(0, h - win, stride):
        for x in range(0, w - win, stride):
            bm = bg_mask[y:y+win, x:x+win]
            if np.sum(bm) < win * win * 0.7:
                continue

            mask = bm & (sat[y:y+win, x:x+win] > 110) & (val[y:y+win, x:x+win] > 130)
            ratio = np.sum(mask) / np.sum(bm)
            max_ratio = max(max_ratio, ratio)

            if ratio > 0.010:
                hit = True

    if hit:
        return 2, f"국소 고채도 단색 영역 감지(max_ratio={max_ratio:.4f})"
    return 0, f"고채도 영역 적음(max_ratio={max_ratio:.4f})"

# ======================================================
# 6. 최종 판단 + 로그
# ======================================================
score = 0
logs = []

s, msg = score_text(img_rgb)
score += s
logs.append(f"[TEXT] +{s} → {msg}")

s, msg = score_edge_density(img_rgb, bg_mask)
score += s
logs.append(f"[EDGE] +{s} → {msg}")

s, msg = score_color_flatness(img_rgb, bg_mask)
score += s
logs.append(f"[COLOR] +{s} → {msg}")

has_logo = score >= 3

print("========== LOGO SCORE DETAIL ==========")
for line in logs:
    print(line)
print("--------------------------------------")
print(f"[FINAL] has_logo={has_logo}, total_score={score}")
print("======================================")
