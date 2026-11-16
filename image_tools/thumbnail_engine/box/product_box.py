# image_tools/thumbnail_engine/box/product_box.py

from .base import Box
from ..config import BOX_RULES


def build_product_box(box: Box, image_size: tuple[int, int]) -> Box:
    """
    상품 박스 보정
    - rembg / yolo 등으로 얻은 object box 기준
    - padding 적용
    - 이미지 영역 clamp
    """

    img_w, img_h = image_size

    # 1️⃣ 상품 전용 패딩 적용 (이미 있는 규칙 사용)
    padding = BOX_RULES.get("product", {}).get("padding")
    if padding:
        box = box.apply_padding(padding)

    # 2️⃣ 이미지 영역 내로 clamp
    # ❗ Box.clamp는 (width, height)만 받는다
    box = box.clamp(img_w, img_h)

    return box
