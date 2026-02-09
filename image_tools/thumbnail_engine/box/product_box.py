# image_tools/thumbnail_engine/box/product_box.py

from .base import Box
from ..config import BOX_RULES


def build_product_box(
    box: Box,
    rule_key: str | None = None
) -> Box:

    # ✅ rule_key가 있으면 그걸, 없으면 기본 "product"
    key = rule_key or "product"

    # 1️⃣ 패딩 적용
    padding = BOX_RULES.get(key, {}).get("padding")
    if padding:
        box = box.apply_padding(padding)

    return box
