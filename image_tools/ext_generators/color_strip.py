# image_tools/color_strip.py

from PIL import Image, ImageDraw
import requests, io
from image_tools.image_fetcher import fetch_image_content  # ✅ 개선된 로더 임포트

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
def make_color_strip(item, chip_size=80, border=6, pad=15, scale_factor=1.5):
    """
    가로형 컬러 스트립 생성
    item.parsed_raw['options'] 내 '색상' 그룹에서 칩 이미지를 추출하여 가로로 배치합니다.
    """
    print("[COLOR_STRIP] make_color_strip called")
    
    # 1. options 리스트에서 group_name이 "색상"인 그룹 찾기
    options = item.parsed_raw.get("options", [])
    color_group = next((g for g in options if g.get("group_name") == "색상"), None)
    
    if not color_group or not color_group.get("values"):
        print("[COLOR_STRIP] ❌ Skipped: No color option group found in item")
        return None

    color_values = color_group["values"]
    print(f"   colors count = {len(color_values)}")

    chips = []
    for c in color_values:
        # 유니클로(chip_image)와 무인양품(chip_url) 키 모두 대응
        chip_url = c.get("chip_image") or c.get("chip_url")
        print(f"   processing chip_url = {chip_url}")
        
        if chip_url:
            circ = create_circle_chip(
                chip_url,
                size=chip_size,
                border=border,
                scale_factor=scale_factor
            )
            if circ:
                chips.append(circ)

    if not chips:
        print("[COLOR_STRIP] ❌ no chips generated")
        return None
    
    print(f"[COLOR_STRIP] ✅ chips generated: {len(chips)}")

    # 2. 캔버스 생성 및 가로 배치
    chip_w, chip_h = chips[0].size

    # 총 너비 = 칩 너비 * 개수 + 패딩 * (개수 - 1)
    total_w = len(chips) * chip_w + (len(chips) - 1) * pad
    strip_h = chip_h

    strip = Image.new("RGBA", (total_w, strip_h), (0, 0, 0, 0))

    x = 0
    for chip in chips:
        # 투명도 유지를 위해 3번째 인자에 chip(mask)을 넣어줍니다.
        strip.paste(chip, (x, 0), chip)
        x += chip_w + pad

    return strip


def make_color_strip_vertical(item, chip_size=80, border=6, pad=15, scale_factor=1.5):
    """
    세로형 컬러 스트립 생성
    item.parsed_raw['options'] 내 '색상' 그룹에서 칩 이미지를 추출합니다.
    """
    # 1. options 리스트에서 group_name이 "색상"인 그룹 찾기
    options = item.parsed_raw.get("options", [])
    color_group = next((g for g in options if g.get("group_name") == "색상"), None)
    
    # 색상 그룹이 없거나 values가 비어있으면 종료
    if not color_group or not color_group.get("values"):
        print("[COLOR_STRIP] Skipped: No color option group found in item")
        return None

    # 2. 색상 값 리스트 추출
    color_values = color_group["values"]
    
    chips = []
    for c in color_values:
        # 유니클로(chip_image)와 무인양품(chip_url) 둘 다 대응
        chip_url = c.get("chip_image") or c.get("chip_url")
        
        if chip_url:
            circ = create_circle_chip(
                chip_url,
                size=chip_size,
                border=border,
                scale_factor=scale_factor
            )
            if circ:
                chips.append(circ)

    # 생성된 칩이 하나도 없으면 종료
    if not chips:
        return None

    # 3. 캔버스 생성 및 배치
    chip_w, chip_h = chips[0].size

    # 총 높이 = 칩 높이 * 개수 + 패딩 * (개수 - 1)
    total_h = len(chips) * chip_h + (len(chips) - 1) * pad
    strip_w = chip_w

    # 투명 배경의 새 이미지 생성
    strip = Image.new("RGBA", (strip_w, total_h), (0, 0, 0, 0))

    y = 0
    for chip in chips:
        # mask 인자에 chip을 넣어 투명도 유지하며 붙이기
        strip.paste(chip, (0, y), chip)
        y += chip_h + pad

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
