# image_tools/thumbnail_engine/box/lower_body_box.py

from .base import Box
from ..config import BOX_RULES

# MediaPipe lower body landmarks
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28


def build_lower_body_box(
    lower_body_box: Box,
    landmarks: dict | None = None,
    image_size: tuple[int, int] | None = None,
    rule_key: str | None = None
) -> Box:
    """
    lower_body_box: 골반~발목 기준 raw 박스
    landmarks: mediapipe pose landmarks (optional)
    image_size: (w, h) for clamp (optional)
    """

    box = lower_body_box
    key = rule_key or "lower_body"

    # --------------------------------------------------
    # 1) 좌우 확장 (다리 벌림 대응)
    # --------------------------------------------------
    if landmarks:
        xs = []

        for idx in (
            LEFT_HIP, RIGHT_HIP,
            LEFT_KNEE, RIGHT_KNEE,
            LEFT_ANKLE, RIGHT_ANKLE,
        ):
            if idx in landmarks:
                xs.append(landmarks[idx][0])

        if xs:
            left = min(xs)
            right = max(xs)

            box = Box(
                x=min(box.left, left),
                y=box.top,
                w=max(box.right, right) - min(box.left, left),
                h=box.h,
            )

    # --------------------------------------------------
    # 2) 패딩
    # --------------------------------------------------
    padding = BOX_RULES[key]["padding"]
    box = box.apply_padding(padding)

    # --------------------------------------------------
    # 3) 이미지 영역 clamp (🔥 필수)
    # --------------------------------------------------
    if image_size:
        img_w, img_h = image_size
        box = box.clamp(img_w, img_h)

    return box
