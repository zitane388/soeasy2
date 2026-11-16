from PIL import Image
from rembg import remove
from io import BytesIO
import os

OUT = "image_tools/thumbnail_engine/tests/_bg_prebuilt_test"
os.makedirs(OUT, exist_ok=True)


def rembg_alpha_only(img: Image.Image) -> Image.Image:
    buf = BytesIO()
    img.save(buf, format="PNG")
    raw = buf.getvalue()

    removed = remove(raw)

    before = Image.open(BytesIO(raw)).convert("RGBA")
    R, G, B, _ = before.split()

    after = Image.open(BytesIO(removed)).convert("RGBA")
    _, _, _, A = after.split()

    return Image.merge("RGBA", (R, G, B, A))


def resize_rgba(img: Image.Image, size):
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img.resize(size, Image.LANCZOS)


def paste_on_prebuilt_bg(
    fg_rgba: Image.Image,
    bg_color=(243, 243, 243),
    canvas_size=(1000, 1000),
    pos=(150, 150),
) -> Image.Image:
    bg = Image.new("RGBA", canvas_size, (*bg_color, 255))
    bg.paste(fg_rgba, pos, fg_rgba.split()[3])
    return bg.convert("RGB")


# --------------------------------------------
# TEST
# --------------------------------------------
src = Image.open(
    "image_tools/thumbnail_engine/tests/assets/test_person.jpg"
).convert("RGBA")

# 1) rembg first
clean = rembg_alpha_only(src)
clean.save(f"{OUT}/01_rembg_alpha_only.png")

# 2) resize
scaled = resize_rgba(clean, (700, 700))
scaled.save(f"{OUT}/02_resized.png")

# 3) paste on prebuilt background
final = paste_on_prebuilt_bg(
    scaled,
    bg_color=(243, 243, 243),
    canvas_size=(1000, 1000),
    pos=(150, 150),
)

final.save(f"{OUT}/03_final.png")

print("DONE")
