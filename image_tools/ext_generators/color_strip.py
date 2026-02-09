# image_tools/color_strip.py

from PIL import Image, ImageDraw
import requests, io
from image_tools.image_fetcher import fetch_image_content  # ✅ 개선된 로더 임포트

def _solve_chip_size(count, border, pad, scale_factor, max_length):
    numerator = max_length - pad * (count - 1)
    denom = count * scale_factor
    size = (numerator / denom) - (2 * border)

    MAX_CHIP = 100  # 🔥 최대 사이즈 제한만 추가

    return min(int(size), MAX_CHIP)


def _build_strip_from_chips(chips, pad):
    chip_w, chip_h = chips[0].size
    total_w = len(chips) * chip_w + (len(chips) - 1) * pad
    strip = Image.new("RGBA", (total_w, chip_h), (0, 0, 0, 0))

    x = 0
    for chip in chips:
        strip.paste(chip, (x, 0), chip)
        x += chip_w + pad
        
    print("\n[STRIP_BUILD_H]")
    print(f" chip_w={chip_w}")
    print(f" pad={pad}")
    print(f" chip_count={len(chips)}")
    print(f" total_w={total_w}")

    return strip


def _build_vertical_strip_from_chips(chips, pad):
    chip_w, chip_h = chips[0].size
    total_h = len(chips) * chip_h + (len(chips) - 1) * pad
    strip = Image.new("RGBA", (chip_w, total_h), (0, 0, 0, 0))

    y = 0
    for chip in chips:
        strip.paste(chip, (0, y), chip)
        y += chip_h + pad
        
    print("\n[STRIP_BUILD_V]")
    print(f" chip_h={chip_h}")
    print(f" pad={pad}")
    print(f" chip_count={len(chips)}")
    print(f" total_h={total_h}")
    return strip



def create_circle_chip(url, size=80, border=6, scale_factor=1.2):
    """
    개선된 fetch_image_content를 사용하여 컬러칩 생성
    """
    print(f"[COLOR_CHIP] fetch (high-speed): {url}")
    final_size = int(size * scale_factor)
    final_border = int(border * scale_factor)

    try:
        # ✅ 개선된 로더 사용 (HTTP/2, MUJI 우회 로직 포함)
        content = fetch_image_content(url)
        
        if not content:
            print(f"[COLOR_CHIP][ERROR] No content for: {url}")
            return None
            
        src = Image.open(io.BytesIO(content)).convert("RGBA")
    except Exception as e:
        print(f"[COLOR_CHIP][ERROR] {url} -> {e}")
        return None

    # -------------------------------------------------------------
    # 1) 고품질 원 생성을 위해 업스케일 후 다시 다운샘플
    # -------------------------------------------------------------
    # 소스 이미지가 작을 경우(95px) 대비하여 업스케일 배율 유지
    upscale = final_size * 4
    src = src.resize((upscale, upscale), Image.LANCZOS)

    # 원형 마스크
    mask = Image.new("L", (upscale, upscale), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, upscale - 1, upscale - 1), fill=255)

    circle = Image.new("RGBA", (upscale, upscale), (0, 0, 0, 0))
    circle.paste(src, (0, 0), mask)

    # 다운샘플로 부드럽게 (안티앨리어싱 효과)
    circle = circle.resize((final_size, final_size), Image.LANCZOS)

    # -------------------------------------------------------------
    # 2) 외부 보더 (내부 색상을 침범하지 않는 흰색 테두리)
    # -------------------------------------------------------------
    canvas_size = final_size + final_border * 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

    # 보더 원 (흰색)
    border_img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border_img)
    bdraw.ellipse(
        (0, 0, canvas_size - 1, canvas_size - 1),
        fill=(255, 255, 255, 255)
    )

    canvas.paste(border_img, (0, 0), border_img)

    # 내부 원(색상/패턴) 중앙 배치
    cx = final_border
    cy = final_border
    canvas.paste(circle, (cx, cy), circle)

    return canvas

# ---------------------------------------------------------
# 컬러칩 strip 생성
# ---------------------------------------------------------
def make_color_strip(item, chip_size=80, border=6, pad=15, scale_factor=1.5, max_width=None):
    options = item.parsed_raw.get("options", [])
    color_group = next((g for g in options if g.get("group_name") == "색상"), None)
    if not color_group or not color_group.get("values"):
        return None

    # ✅ 최대 8개 제한
    color_values = color_group["values"][:7]
    count = len(color_values)

    print("\n[COLOR_STRIP_H_START]")
    print(f" color_count(original)={len(color_group['values'])}")
    print(f" color_count(used)={count}")

    if max_width:
        chip_size = _solve_chip_size(count, border, pad, scale_factor, max_width)

    chips = []
    for c in color_values:
        url = c.get("chip_image") or c.get("chip_url")
        chip = create_circle_chip(url, size=chip_size, border=border, scale_factor=scale_factor)
        if chip:
            chips.append(chip)

    if not chips:
        return None

    strip = _build_strip_from_chips(chips, pad)
    return strip




def make_color_strip_vertical(item, chip_size=80, border=6, pad=15, scale_factor=1.5, max_height=None):
    options = item.parsed_raw.get("options", [])
    color_group = next((g for g in options if g.get("group_name") == "색상"), None)
    if not color_group or not color_group.get("values"):
        return None

    # ✅ 최대 8개 제한
    color_values = color_group["values"][:7]
    count = len(color_values)

    print("\n[COLOR_STRIP_V_START]")
    print(f" color_count(original)={len(color_group['values'])}")
    print(f" color_count(used)={count}")

    if max_height:
        chip_size = _solve_chip_size(count, border, pad, scale_factor, max_height)

    chips = []
    for c in color_values:
        url = c.get("chip_image") or c.get("chip_url")
        chip = create_circle_chip(url, size=chip_size, border=border, scale_factor=scale_factor)
        if chip:
            chips.append(chip)

    if not chips:
        return None

    strip = _build_vertical_strip_from_chips(chips, pad)
    return strip






# ---------------------------------------------------------
# strip을 썸네일에 합성
# ---------------------------------------------------------
def apply_color_strip_to_thumbnail(thumbnail_img, color_strip, position="h-left-top", offset=(40, 40)):
    """
    position:
        - h-left-top
        - h-right-top
        - h-left-bottom
        - h-right-bottom
        - v-left-top
        - v-right-top
        - v-left-bottom
        - v-right-bottom
    """
    
    if thumbnail_img.mode != "RGBA":
        thumbnail_img = thumbnail_img.convert("RGBA")

    out = thumbnail_img.copy()

    tw, th = out.size
    sw, sh = color_strip.size
    ox, oy = offset
    
    print("\n[CANVAS_INFO]")
    print(f" canvas_w={tw}, strip_w={sw}, margin_x={ox*2}")
    print(f" canvas_h={th}, strip_h={sh}, margin_y={oy*2}")



    # -------------------------------
    # 가로/세로 strip 방향 구분
    # -------------------------------
    is_vertical = position.startswith("v-")

    if is_vertical:
        # 세로 strip: width=sw, height=sh
        pass
    else:
        # 가로 strip
        pass

    # -------------------------------
    # Left / Right
    # -------------------------------
    if "left" in position:
        x = ox
    else:  # right
        x = tw - sw - ox

    # -------------------------------
    # Top / Bottom
    # -------------------------------
    if "top" in position:
        y = oy
    else:  # bottom
        y = th - sh - oy

    out.paste(color_strip, (x, y), color_strip)

    return out


# ==========================================================
# 단독 테스트용 main
# ==========================================================
if __name__ == "__main__":
    print("🔵 color_strip 테스트 시작")

    # 테스트용 칩 이미지 URL 3개 (유니클로 컬러칩 등 아무거나 넣어도 됨)
    TEST_COLORS = [
        "https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/478557/chip/goods_09_478557_chip.jpg",
        "https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/478557/chip/goods_05_478557_chip.jpg",
        "https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/478557/chip/goods_38_478557_chip.jpg",
    ]

    # 테스트용 가짜 item 객체 만들기
    class DummyItem:
        def __init__(self, urls):
            self.parsed_raw = {
                "colors": [{"chip_image": u} for u in urls]
            }

    item = DummyItem(TEST_COLORS)

    # strip 생성
    strip = make_color_strip(item, chip_size=80, border=6, pad=30)

    if strip is None:
        print("❌ strip 생성 실패")
    else:
        out_path = "color_strip_test.png"
        strip.save(out_path)
        print(f"✅ strip 생성 완료 → {out_path}")
