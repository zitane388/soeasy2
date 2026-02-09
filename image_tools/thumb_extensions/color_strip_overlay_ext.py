# image_tools/thumbnail_extensions/color_strip.py

from PIL import Image
import traceback
from image_tools.ext_generators.color_strip import (
    make_color_strip,
    make_color_strip_vertical
)

def color_strip_ext(item, img, ext_state):
    try:
        enabled = ext_state.get("color_strip_extra")
        if hasattr(enabled, "get"):
            enabled = enabled.get()
        if not enabled:
            return None

        brand = str(getattr(item, "brand", "")).strip().lower()
        country = str(getattr(item, "country", "")).strip().lower()

        if brand not in ["유니클로","uniqlo","gu","지유","muji","무인양품"]:
            return None

        options = item.parsed_raw.get("options", [])
        color_group = next((g for g in options if g.get("group_name") == "색상"), None)
        if not color_group or not color_group.get("values"):
            return None

        position = ext_state.get("color_strip_extra_position", "h-left-top")
        if hasattr(position, "get"):
            position = position.get()

        is_vertical = position.startswith("v-")
        W, H = img.size
        SAFE_MARGIN = 40

        # 🔥 크기 계산은 생성단계에서만!
        if is_vertical:
            strip = make_color_strip_vertical(
                item,
                chip_size=90,
                pad=18,
                max_height=H - SAFE_MARGIN
            )
        else:
            strip = make_color_strip(
                item,
                chip_size=90,
                pad=18,
                max_width=W - SAFE_MARGIN
            )

        if strip is None:
            return None

        sw, sh = strip.size
        out = img.copy()

        x = 40 if "-left-" in position else (W - sw - 40)
        y = 40 if position.endswith("top") else (H - sh - 40)

        out.paste(strip, (x, y), strip)
        return out

    except Exception:
        traceback.print_exc()
        return None
