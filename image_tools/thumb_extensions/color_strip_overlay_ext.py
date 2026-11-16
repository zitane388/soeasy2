# image_tools/thumbnail_extensions/color_strip.py

from PIL import Image
from image_tools.ext_generators.color_strip import (
    make_color_strip,
    make_color_strip_vertical
)


import traceback
from PIL import Image
from image_tools.ext_generators.color_strip import (
    make_color_strip,
    make_color_strip_vertical
)

def color_strip_ext(item, img, ext_state):
    print("\n" + "="*40)
    print("[COLOR_STRIP] PROCESS START")
    
    try:
        # ------------------------------------------
        # 1) 옵션 체크 (Tkinter 객체 대응)
        # ------------------------------------------
        enabled = ext_state.get("color_strip_extra")
        
        # 실행파일 환경에서 BooleanVar 객체가 넘어올 경우를 대비해 .get() 처리
        if hasattr(enabled, "get"):
            enabled = enabled.get()
            
        if not enabled:
            print("[COLOR_STRIP] Skipped: Option is disabled")
            return None

        # ------------------------------------------
        # 2) 브랜드/국가 조건 확인
        # ------------------------------------------
        brand = str(getattr(item, "brand", "")).strip().lower()
        country = str(getattr(item, "country", "")).strip().lower()
        
        print(f"[COLOR_STRIP] Brand: {brand}, Country: {country}")

        # 한글/영문 모두 대응
        is_uniqlo = (brand in ["유니클로", "uniqlo"])
        is_gu = (brand in ["gu", "지유"])
        is_muji = (brand in ["muji", "무인양품"])

        if is_uniqlo:
            if country not in ["jp", "vn"]:
                print(f"[COLOR_STRIP] Skipped: Uniqlo country {country} not supported")
                return None
        elif is_gu:
            if country != "jp":
                print(f"[COLOR_STRIP] Skipped: GU country {country} not supported")
                return None
        elif is_muji:
            if country != "jp":
                print(f"[COLOR_STRIP] Skipped: GU country {country} not supported")
                return None
        else:
            print(f"[COLOR_STRIP] Skipped: Unsupported brand {brand}")
            return None

        # ------------------------------------------
        # 3) 색상 데이터 확인
        # ------------------------------------------
        options = item.parsed_raw.get("options", [])
        color_group = next((g for g in options if g.get("group_name") == "색상"), None)
        if not color_group or not color_group.get("values"):
            print("[COLOR_STRIP] Skipped: No color option group found in item")
            return None

        # ------------------------------------------
        # 4) 위치 옵션 및 스트립 생성
        # ------------------------------------------
        position = ext_state.get("color_strip_extra_position", "h-left-top")
        if hasattr(position, "get"):
            position = position.get()
            
        is_vertical = position.startswith("v-")
        print(f"[COLOR_STRIP] Position: {position} (Vertical: {is_vertical})")

        # 스트립 생성 시도
        if is_vertical:
            strip = make_color_strip_vertical(item, chip_size=90, pad=18)
        else:
            strip = make_color_strip(item, chip_size=90, pad=18)

        if strip is None:
            # make_color_strip 내부에서 requests 에러 등이 발생했을 확률 높음
            print("[COLOR_STRIP] Error: make_color_strip returned None")
            return None

        # ------------------------------------------
        # 5) 좌표 계산 및 합성
        # ------------------------------------------
        sw, sh = strip.size
        W, H = img.size
        out = img.copy()

        # x 좌표 (좌/우)
        x = 40 if "-left-" in position else (W - sw - 40)
        # y 좌표 (상/하)
        y = 40 if position.endswith("top") else (H - sh - 40)

        out.paste(strip, (x, y), strip)
        print("[COLOR_STRIP] Successfully applied color strip")
        return out

    except Exception as e:
        print(f"[COLOR_STRIP] !! CRITICAL ERROR: {e}")
        traceback.print_exc() # 실행파일 콘솔에서 에러 원인을 상세히 보기 위함
        return None
    finally:
        print("[COLOR_STRIP] PROCESS END")
        print("="*40 + "\n")
