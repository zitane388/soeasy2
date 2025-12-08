# pp_focus.py
# 완성본 — 인물/상품 안전 스케일 조정 + Mediapipe/YOLO + 배경색 자동 추출 + 경계 부드러움 개선

import cv2
import numpy as np
from PIL import Image
import mediapipe as mp
import torch
print(torch.cuda.is_available())
import time, os
from io import BytesIO
from PIL import ImageFilter, ImageEnhance

# rembg 세션은 별도 생성하지 않음 → app_startup.py에서 preload된 SESSION 사용
from rembg import remove
from app_startup import SESSION, YOLO_MODEL

print(f"🚀 YOLO Model Device    : {YOLO_MODEL.device}")

mp_pose = mp.solutions.pose

FINAL_SIZE = 1000
BASE_LEFT_W = 540
BASE_RIGHT_W = 460

RIGHT_W_CANDIDATES = [460, 520, 580, 620, 650]

TARGET_LEG_RATIO = 0.80
TARGET_PRODUCT_RATIO = 0.85



# ============================================================
# 인물 이미지 로드
# ============================================================
def load_person(path):
    return Image.open(path).convert("RGBA")


# ============================================================
# Mediapipe 다리 박스 탐지
# ============================================================
def detect_leg_box(path):
    img = cv2.imread(path)
    if img is None:
        return None

    h, w, _ = img.shape
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    with mp_pose.Pose(static_image_mode=True) as pose:
        res = pose.process(rgb)

    if not res.pose_landmarks:
        return None

    lm = res.pose_landmarks.landmark
    indices = [23, 24, 25, 26, 27, 28, 31, 32]

    xs, ys = [], []
    for idx in indices:
        if lm[idx].visibility < 0.3:
            continue
        xs.append(lm[idx].x * w)
        ys.append(lm[idx].y * h)

    if len(xs) < 2:
        return None

    return {
        "left": min(xs),
        "right": max(xs),
        "top": min(ys),
        "bottom": max(ys),
        "w": w,
        "h": h
    }


def detect_leg_box_with_fallback(image_path):
    box = detect_leg_box(image_path)
    if box:
        return box

    print("⚠ Mediapipe 실패 → YOLO person box 사용")

    results = YOLO_MODEL.predict(image_path, conf=0.25, classes=[0], verbose=False)
    if not results[0].boxes:
        return None

    b = results[0].boxes[0]
    x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()

    return {
        "left": x1,
        "right": x2,
        "top": y1,
        "bottom": y2,
        "w": x2 - x1,
        "h": y2 - y1
    }


# ============================================================
# 인물 확대 + 안전 스케일링 + 크롭 방지 기능
# ============================================================
def scale_and_position_person(img, pose_legs, LEFT_W):
    orig_w, orig_h = img.size

    leg_h = pose_legs["y_bottom"] - pose_legs["y_top"]
    target_leg_h = FINAL_SIZE * TARGET_LEG_RATIO
    base_scale = target_leg_h / leg_h

    scales = [base_scale * (0.95 ** i) for i in range(25)]

    print("\n=========================")
    print("인물 배치(Mediapipe 다리 박스 중심 기준) 시작")
    print("=========================")

    for attempt, sc in enumerate(scales, start=1):

        new_w = int(orig_w * sc)
        new_h = int(orig_h * sc)
        person_scaled = img.resize((new_w, new_h), Image.LANCZOS)

        # 스케일 적용된 다리 박스 좌표
        x_min_s = pose_legs["x_min"] * sc
        x_max_s = pose_legs["x_max"] * sc
        y_top_s = pose_legs["y_top"] * sc
        y_bottom_s = pose_legs["y_bottom"] * sc

        # 🔥 하체 중심 좌표
        leg_center_x = (x_min_s + x_max_s) / 2

        # 🔥 인물 영역 LEFT_W 가운데 정렬
        offset_x = (LEFT_W / 2) - leg_center_x

        # 세로 배치
        leg_center_y = (y_top_s + y_bottom_s) / 2
        desired_center_y = FINAL_SIZE / 2
        offset_y = desired_center_y - leg_center_y

        # 보정
        if offset_y > 0 and offset_y + new_h < FINAL_SIZE:
            offset_y = FINAL_SIZE - new_h
        if offset_y < 0 and offset_y + new_h > FINAL_SIZE:
            offset_y = 0

        # 실제 위치 계산
        px1 = x_min_s + offset_x
        px2 = x_max_s + offset_x
        py1 = y_top_s + offset_y
        py2 = y_bottom_s + offset_y

        crop_left   = px1 < 0
        crop_right  = px2 > LEFT_W
        crop_top    = py1 < 0
        crop_bottom = py2 > FINAL_SIZE

        print(f"\n[인물 시도 {attempt}]")
        print(f"scale = {sc:.4f}")
        print(f"leg_center_x={leg_center_x:.2f}, offset_x={offset_x:.2f}")
        print(f"px1={px1:.2f}, px2={px2:.2f}, LEFT_W={LEFT_W}")
        print(f"crop: left={crop_left}, right={crop_right}, top={crop_top}, bottom={crop_bottom}")

        # 성공 조건
        if not (crop_left or crop_right or crop_top or crop_bottom):
            print("✅ 인물 안전 — 크롭 없음 → 스케일 확정")
            return person_scaled, offset_x, offset_y

        print("❌ 인물 크롭 발생 → 스케일 감소")

        # 디버그 이미지 저장
        debug_img = Image.new("RGBA", (LEFT_W, FINAL_SIZE), (255,255,255,255))
        debug_img.paste(person_scaled, (int(offset_x), int(offset_y)), person_scaled)
        debug_img.save(f"person_crop_attempt_{attempt}.png")

    # 최종 fallback
    sc = scales[-1]
    new_w = int(orig_w * sc)
    new_h = int(orig_h * sc)
    person_scaled = img.resize((new_w, new_h), Image.LANCZOS)

    leg_center_x = ((pose_legs["x_min"] + pose_legs["x_max"]) / 2) * sc
    offset_x = (LEFT_W / 2) - leg_center_x
    offset_y = 0

    return person_scaled, offset_x, offset_y


# ============================================================
# 인물 영역 배치
# ============================================================
def extract_background_color(image, sample=30):
    np_img = np.array(image)
    if np_img.shape[2] == 4:
        np_img = np_img[:, :, :3]

    h, w, _ = np_img.shape
    s = sample

    corners = [
        np_img[0:s, 0:s],
        np_img[0:s, w - s:w],
        np_img[h - s:h, 0:s],
        np_img[h - s:h, w - s:w],
    ]

    samples = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
    mean_color = samples.mean(axis=0).astype(np.uint8)
    return tuple(mean_color.tolist())


def place_person(person_scaled, ox, oy, LEFT_W):
    # 투명 배경 유지
    canvas = Image.new("RGBA", (LEFT_W, FINAL_SIZE), (255,255,255,0))
    canvas.paste(person_scaled, (int(ox), int(oy)), person_scaled)
    return canvas


# ============================================================
# YOLO 상품 탐지
# ============================================================
def detect_obj(path):
    res = YOLO_MODEL.predict(path, conf=0.3, verbose=False)
    boxes = res[0].boxes

    if len(boxes) == 0:
        img = Image.open(path)
        w, h = img.size
        return [0, 0, w, h]

    xs1, ys1, xs2, ys2 = [], [], [], []
    for b in boxes:
        x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().tolist()
        xs1.append(x1)
        ys1.append(y1)
        xs2.append(x2)
        ys2.append(y2)

    return [
        int(min(xs1)),
        int(min(ys1)),
        int(max(xs2)),
        int(max(ys2)),
    ]


# ============================================================
# 상품 로드
# ============================================================
def load_product(path):
    yolo_box = detect_obj(path)
    img = Image.open(path).convert("RGBA")   # BG 제거 안함
    return img, yolo_box


def extract_dominant_bg_color(img):
    np_img = np.array(img)
    if np_img.shape[2] == 4:
        np_img = np_img[:, :, :3]

    h, w, _ = np_img.shape
    s = 30

    corners = [
        np_img[0:s, 0:s],
        np_img[0:s, w - s:w],
        np_img[h - s:h, 0:s],
        np_img[h - s:h, w - s:w],
    ]

    samples = np.concatenate([c.reshape(-1, 3) for c in corners], axis=0)
    mean_color = samples.mean(axis=0).astype(np.uint8)
    return tuple(mean_color.tolist())


# ============================================================
# 상품 안전 배치
# ============================================================
def safe_place_product(prod, RIGHT_W, yolo_box):
    px1, py1, px2, py2 = yolo_box
    pw, ph = prod.size

    box_cx = (px1 + px2) / 2
    box_h = py2 - py1

    target_h = FINAL_SIZE * TARGET_PRODUCT_RATIO
    scale = target_h / box_h

    attempt = 0
    while True:
        attempt += 1

        new_w = int(pw * scale)
        new_h = int(ph * scale)
        prod_scaled = prod.resize((new_w, new_h), Image.LANCZOS)

        r_px1 = px1 * scale
        r_px2 = px2 * scale
        r_box_cx = box_cx * scale

        offset_x = (RIGHT_W / 2) - r_box_cx

        left_crop = (r_px1 + offset_x) < 0
        right_crop = (r_px2 + offset_x) > RIGHT_W

        if not (left_crop or right_crop):
            break

        scale *= 0.93
        if scale < 0.05:
            break

    # 최종 스케일 적용
    new_w = int(pw * scale)
    new_h = int(ph * scale)
    prod_scaled = prod.resize((new_w, new_h), Image.LANCZOS)

    offset_x = (RIGHT_W / 2) - (box_cx * scale)
    offset_y = (FINAL_SIZE - new_h) // 2

    canvas = Image.new("RGBA", (RIGHT_W, FINAL_SIZE), (255,255,255,0))
    canvas.paste(prod_scaled, (int(offset_x), int(offset_y)), prod_scaled)

    return canvas


# ============================================================
# 최종 합성
# ============================================================
def merge(person_area, product_area, LEFT_W):
    final = Image.new("RGBA", (FINAL_SIZE, FINAL_SIZE), (255, 255, 255, 255))
    final.paste(person_area, (0, 0), person_area)
    final.paste(product_area, (LEFT_W, 0), product_area)
    return final




# 🔥 rembg / HuggingFace 캐시 강제 지정
os.environ["HF_HOME"] = "./hf_cache"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["XDG_CACHE_HOME"] = "./hf_cache"



def remove_person_background(img_path: str) -> Image.Image:
    print("\n🔍 [LOG] remove_person_background() 시작")
    t0 = time.time()

    with open(img_path, "rb") as f:
        input_data = f.read()

    t1 = time.time()
    print(f"   ⏱ 파일 로드 시간: {t1 - t0:.2f}초")

    t2 = time.time()
    output_data = remove(input_data, session=SESSION)
    t3 = time.time()
    print(f"   ⏱ rembg(remove) 처리 시간: {t3 - t2:.2f}초")

    img = Image.open(BytesIO(output_data)).convert("RGBA")

    t4 = time.time()
    print(f"   ⏱ PIL 변환 시간: {t4 - t3:.2f}초")
    print("🔍 [LOG] remove_person_background() 종료\n")

    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=0.4))
    img = Image.merge("RGBA", (r, g, b, a))

    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.04)

    return img


def remove_product_background(img_path: str) -> Image.Image:
    print("\n🔍 [LOG] remove_product_background() 시작")
    t0 = time.time()

    with open(img_path, "rb") as f:
        input_data = f.read()

    t1 = time.time()
    print(f"   ⏱ 파일 로드 시간: {t1 - t0:.2f}초")

    t2 = time.time()
    output_data = remove(input_data, session=SESSION)
    t3 = time.time()
    print(f"   ⏱ rembg(remove) 처리 시간: {t3 - t2:.2f}초")

    img = Image.open(BytesIO(output_data)).convert("RGBA")

    t4 = time.time()
    print(f"   ⏱ PIL 변환 시간: {t4 - t3:.2f}초")
    print("🔍 [LOG] remove_product_background() 종료\n")

    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=0.4))
    img = Image.merge("RGBA", (r, g, b, a))

    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.03)

    return img


# ============================================================
# 전체 파이프라인 (기존: 파일 경로 2개 + output 경로)
# ============================================================
def generate_thumbnail(img1_path, img2_path, output_path):
    """
    기존 CLI용 로직 그대로 유지.
    img1_path : 인물 이미지 경로
    img2_path : 상품 이미지 경로
    output_path : 결과 썸네일 PNG 경로
    실패 시 예외 발생.
    """
    print(f"\n[THUMB] generate_thumbnail() 시작")
    print(f"  person = {img1_path}")
    print(f"  product = {img2_path}")
    print(f"  output = {output_path}")

    if not os.path.exists(img1_path):
        raise FileNotFoundError(f"인물 이미지 없음: {img1_path}")
    if not os.path.exists(img2_path):
        raise FileNotFoundError(f"상품 이미지 없음: {img2_path}")

    # 상품 처리
    prod, yolo_box = load_product(img2_path)

    RIGHT_W = BASE_RIGHT_W
    for w in RIGHT_W_CANDIDATES:
        RIGHT_W = w
        pw, ph = prod.size
        test_scale = min(w / pw, FINAL_SIZE / ph)
        if ph * test_scale > FINAL_SIZE * 0.55:
            break

    LEFT_W = FINAL_SIZE - RIGHT_W

    # 인물 처리
    person = Image.open(img1_path).convert("RGBA")
    leg_box = detect_leg_box_with_fallback(img1_path)
    if not leg_box:
        raise RuntimeError("Leg detection failed (Mediapipe & YOLO 모두 실패)")

    pose_legs = {
        "x_min": leg_box["left"],
        "x_max": leg_box["right"],
        "y_top": leg_box["top"],
        "y_bottom": leg_box["bottom"]
    }

    person_scaled, ox, oy = scale_and_position_person(person, pose_legs, LEFT_W)
    person_area = place_person(person_scaled, ox, oy, LEFT_W)

    product_area = safe_place_product(prod, RIGHT_W, yolo_box)

    final = merge(person_area, product_area, LEFT_W)

    # 전체 합성 후 배경 제거 (BiRefNet)
    final_bytes = BytesIO()
    final.save(final_bytes, format="PNG")
    output_data = remove(final_bytes.getvalue(), session=SESSION)
    final = Image.open(BytesIO(output_data)).convert("RGBA")

    # 결과 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.save(output_path)
    print(f"[THUMB] 썸네일 저장 완료 → {output_path}")


# ============================================================
# GUI용 헬퍼 1: 로컬 경로 2개로부터 생성 + 실패 대응
# ============================================================
def generate_thumbnail_from_paths(person_path, product_path, output_path):
    """
    GUI에서 직접 파일 경로 2개를 넘길 때 사용.
    성공 : (True, output_path)
    실패 : (False, 에러메시지)
    """
    try:
        generate_thumbnail(person_path, product_path, output_path)
        return True, output_path
    except Exception as e:
        print("[THUMB][ERROR] generate_thumbnail_from_paths 실패:", e)
        return False, str(e)


# ============================================================
# GUI용 헬퍼 2: URL 2개 → temp_img 폴더에 저장 후 썸네일 생성
# ============================================================
import requests
from datetime import datetime


def generate_thumbnail_from_urls(person_url, product_url,
                                 temp_dir="temp_img",
                                 output_path=None):
    """
    체크박스로 선택된 2개 이미지가 URL일 때 사용.
    1) temp_img 폴더에 각각 다운로드
    2) generate_thumbnail() 호출
    성공 : (True, 결과파일경로)
    실패 : (False, 에러메시지)
    """
    try:
        os.makedirs(temp_dir, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        person_path = os.path.join(temp_dir, f"person_{ts}.png")
        product_path = os.path.join(temp_dir, f"product_{ts}.png")

        # ------------ 인물 다운로드 ------------
        print(f"[THUMB] 인물 URL 다운로드: {person_url}")
        r1 = requests.get(person_url, timeout=15)
        if r1.status_code != 200:
            return False, f"인물 이미지 다운로드 실패 (status={r1.status_code})"
        with open(person_path, "wb") as f:
            f.write(r1.content)

        # ------------ 상품 다운로드 ------------
        print(f"[THUMB] 상품 URL 다운로드: {product_url}")
        r2 = requests.get(product_url, timeout=15)
        if r2.status_code != 200:
            return False, f"상품 이미지 다운로드 실패 (status={r2.status_code})"
        with open(product_path, "wb") as f:
            f.write(r2.content)

        # ------------ 출력 경로 ------------
        if output_path is None:
            output_path = os.path.join(temp_dir, f"thumb_{ts}.png")

        ok, info = generate_thumbnail_from_paths(person_path, product_path, output_path)
        return ok, info

    except Exception as e:
        print("[THUMB][ERROR] generate_thumbnail_from_urls 실패:", e)
        return False, str(e)
