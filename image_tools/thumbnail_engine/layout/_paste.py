# image_tools/thumbnail_engine/layout/_paste.py

from PIL import Image

def paste_with_policy(canvas: Image.Image, slot: Image.Image, xy: tuple[int, int], remove_bg: bool):
    if slot.mode != "RGBA":
        slot = slot.convert("RGBA")

    if remove_bg:
        alpha = slot.split()[3]  # ✅ 알파채널만 mask로
        canvas.paste(slot, xy, alpha)
    else:
        canvas.paste(slot, xy)
