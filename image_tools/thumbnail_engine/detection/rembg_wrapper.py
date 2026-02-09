# image_tools/thumbnail_engine/detection/rembg_wrapper.py

from rembg import remove
from PIL import Image
from io import BytesIO
from app_startup import SESSION


def extract_alpha_mask(pil_image: Image.Image) -> Image.Image:
    """
    rembg를 이용해 알파 마스크만 추출
    (RGB는 절대 사용하지 않음)
    """
    buf = BytesIO()
    pil_image.save(buf, format="PNG")

    removed_bytes = remove(buf.getvalue(), session=SESSION)

    _, _, _, alpha = (
        Image.open(BytesIO(removed_bytes))
        .convert("RGBA")
        .split()
    )

    return alpha
