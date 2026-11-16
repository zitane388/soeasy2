# image_tools/thumbnail_engine/detection/rembg_detector.py

from __future__ import annotations

from io import BytesIO
import numpy as np
from PIL import Image
from rembg import remove

from ..box.base import Box
from ..logger import get_logger

log = get_logger()


class RembgDetector:
    """
    범용 상품 감지기
    - rembg로 전경(알파)만 얻고 bbox만 산출
    - 배경 제거 결과를 '최종 이미지'로 쓰지 않는다
    """

    def detect_object_box_from_path(self, image_path: str) -> Box | None:
        log.info("[REMBG] object detection start path=%s", image_path)

        with open(image_path, "rb") as f:
            src_bytes = f.read()

        # product_focus와 동일: bytes -> remove -> bytes
        raw = remove(src_bytes)
        if not isinstance(raw, (bytes, bytearray)):
            # rembg 버전에 따라 PIL을 주는 경우가 있어 방어
            buf = BytesIO()
            raw.convert("RGBA").save(buf, format="PNG")
            raw = buf.getvalue()

        try:
            img = Image.open(BytesIO(raw)).convert("RGBA")
        except Exception as e:
            log.exception("[REMBG] result decode failed: %s", e)
            return None

        arr = np.array(img)
        alpha = arr[:, :, 3]
        ys, xs = np.where(alpha > 10)

        if len(xs) == 0 or len(ys) == 0:
            log.warning("[REMBG] no foreground detected")
            return None

        x1 = int(xs.min())
        y1 = int(ys.min())
        x2 = int(xs.max())
        y2 = int(ys.max())

        box = Box(x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1))

        log.info("[REMBG] object box x=%d y=%d w=%d h=%d", box.x, box.y, box.w, box.h)
        return box