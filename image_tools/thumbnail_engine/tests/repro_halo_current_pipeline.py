# repro_halo_current_pipeline.py
# 목적: "현재 안되는 구조"를 테스트 코드로 완벽 재현
# 핵심: (레이아웃/슬롯/합성) → RGB로 변환 → (그 뒤) rembg 를 하면 halo가 생김
# 반대: rembg → resize → paste → RGB 는 비교적 깨끗함

from PIL import Image
from rembg import remove
from io import BytesIO
import os
import numpy as np

OUT = "image_tools/thumbnail_engine/tests/_repro_current_fail"
os.makedirs(OUT, exist_ok=True)

SRC_PATH = "image_tools/thumbnail_engine/tests/assets/test_person.jpg"
BG = (243, 243, 243)
CANVAS_SIZE = (1000, 1000)

# -----------------------------
# helpers
# -----------------------------
def save(img: Image.Image, name: str):
    path = os.path.join(OUT, name)
    img.save(path)
    print("[SAVED]", path, img.size, img.mode)

def rembg_alpha_only(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    buf = BytesIO()
    img.save(buf, format="PNG")
    raw = buf.getvalue()

    removed = remove(raw)  # session 사용중이면 remove(raw, session=SESSION) 로 바꾸세요

    before = Image.open(BytesIO(raw)).convert("RGBA")
    R, G, B, _ = before.split()

    after = Image.open(BytesIO(removed)).convert("RGBA")
    _, _, _, A = after.split()

    return Image.merge("RGBA", (R, G, B, A))

def rgba_to_rgb_on_bg(img: Image.Image, bg_color=(243, 243, 243)) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    bg = Image.new("RGBA", img.size, (*bg_color, 255))
    # PIL alpha-composite 방식 (문제 재현 목적)
    bg.paste(img, (0, 0), img)
    return bg.convert("RGB")

def resize_aspect_fit_bad_like_current(img: Image.Image, target_w: int, target_h: int, bg=(0,0,0,0)) -> Image.Image:
    # "현재 구조" 재현: RGBA로 resize(LANCZOS) → 캔버스에 paste(mask=img 자체)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    iw, ih = img.size
    scale = min(target_w / iw, target_h / ih)
    nw = max(1, int(iw * scale))
    nh = max(1, int(ih * scale))

    resized = img.resize((nw, nh), Image.LANCZOS)

    canvas = Image.new("RGBA", (target_w, target_h), bg)
    x = (target_w - nw) // 2
    y = (target_h - nh) // 2

    canvas.paste(resized, (x, y), resized)  # 현재 코드 스타일 재현
    return canvas

def vertical_slot_layout_like_current(images, canvas_size=(1000,1000), background_color=(243,243,243), to_rgb=True):
    canvas_w, canvas_h = canvas_size
    n = len(images)
    slot_h = canvas_h // n
    slot_heights = [slot_h] * n
    slot_heights[-1] = canvas_h - slot_h * (n - 1)

    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    y = 0
    for i, img in enumerate(images):
        h = slot_heights[i]
        img_rgba = img.convert("RGBA")
        slot = resize_aspect_fit_bad_like_current(img_rgba, canvas_w, h, bg=(0,0,0,0))
        canvas.paste(slot, (0, y), slot.split()[3])
        y += h

    if to_rgb:
        return rgba_to_rgb_on_bg(canvas, background_color)
    return canvas

def edge_crop(img: Image.Image, name: str, box=(420, 260, 580, 420)):
    # 경계 근처 확대 확인용 (원하면 box 수정)
    crop = img.crop(box)
    save(crop, name)

# -----------------------------
# TEST
# -----------------------------
src = Image.open(SRC_PATH).convert("RGBA")
save(src, "00_src_rgba.png")

# ==========================================================
# FAIL 재현 (현재 안되는 구조)
# 1) 원본을 그냥 resize/paste/layout 해서 "RGB로 변환"
# 2) 그 결과물을 다시 RGBA로 바꾸고 rembg 실행
#    => halo 유발 (배경이 이미 섞인 RGB를 rembg가 보고 마스크 생성)
# ==========================================================
# 레이아웃/슬롯에서 한 번 더 만져지는 상황을 일부러 재현
stage1_slot = resize_aspect_fit_bad_like_current(src, 1000, 1000, bg=(0,0,0,0))
save(stage1_slot, "01A_slot_rgba_before_rgb.png")

stage2_rgb = rgba_to_rgb_on_bg(stage1_slot, BG)
save(stage2_rgb, "02A_after_rgb_convert.png")
edge_crop(stage2_rgb, "02A_edge_crop.png")

# "레이아웃 다 끝난 뒤 rembg 한 번" 같은 상황 재현
stage3_rgba_again = stage2_rgb.convert("RGBA")
save(stage3_rgba_again, "03A_rgb_to_rgba_again.png")

stage4_rembg_after = rembg_alpha_only(stage3_rgba_again)
save(stage4_rembg_after, "04A_rembg_after_layout.png")

finalA = rgba_to_rgb_on_bg(stage4_rembg_after, BG)
save(finalA, "05A_final_rgb.png")
edge_crop(finalA, "05A_edge_crop.png")

# ==========================================================
# PASS 비교 (네가 성공한 구조)
# 1) 원본에 rembg 먼저
# 2) 그 다음 resize/paste/layout
# 3) 마지막에 RGB 합성
# ==========================================================
clean = rembg_alpha_only(src)
save(clean, "01B_rembg_first_rgba.png")

clean_slot = resize_aspect_fit_bad_like_current(clean, 1000, 1000, bg=(0,0,0,0))
save(clean_slot, "02B_slot_after_rembg.png")

finalB = rgba_to_rgb_on_bg(clean_slot, BG)
save(finalB, "03B_final_rgb.png")
edge_crop(finalB, "03B_edge_crop.png")

print("DONE. Compare A vs B. 특히 *_edge_crop.png 를 확대해서 경계 확인하세요.")
