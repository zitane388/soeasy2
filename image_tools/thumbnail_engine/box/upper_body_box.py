from .base import Box
from ..config import BOX_RULES
# MediaPipe landmark indices
LEFT_HIP = 23
RIGHT_HIP = 24

# arms
ARM_LANDMARKS = [11, 12, 13, 14, 15, 16]


def build_upper_body_box(
    upper_body_box: Box,
    face_box: Box | None,
    landmarks: dict | None = None,
) -> Box:

    # --------------------------------------------------
    # 0) 얼굴 + 상체 merge (기본 영역 확보)
    # --------------------------------------------------
    if face_box:
        x1 = min(upper_body_box.left, face_box.left)
        y1 = min(upper_body_box.top, face_box.top)
        x2 = max(upper_body_box.right, face_box.right)
        y2 = max(upper_body_box.bottom, face_box.bottom)
        box = Box(x=x1, y=y1, w=x2 - x1, h=y2 - y1)
    else:
        box = upper_body_box

    # --------------------------------------------------
    # 1) 얼굴 절반 컷 (상단)
    # --------------------------------------------------
    if face_box:
        face_half_y = face_box.top + face_box.h * 0.5
        if box.top < face_half_y < box.bottom:
            box = Box(
                x=box.x,
                y=face_half_y,
                w=box.w,
                h=box.bottom - face_half_y,
            )

    # --------------------------------------------------
    # 2) 하단 제한: hip 기준 (상체 정의의 핵심)
    # --------------------------------------------------
    if landmarks:
        hips_y = []

        if LEFT_HIP in landmarks:
            hips_y.append(landmarks[LEFT_HIP][1])
        if RIGHT_HIP in landmarks:
            hips_y.append(landmarks[RIGHT_HIP][1])

        if hips_y:
            hip_y = max(hips_y)
            if box.top < hip_y < box.bottom:
                box = Box(
                    x=box.x,
                    y=box.y,
                    w=box.w,
                    h=hip_y - box.y,
                )

    # --------------------------------------------------
    # 3) 팔 포함 (좌우 확장)
    # --------------------------------------------------
    if landmarks:
        xs = []
        for idx in ARM_LANDMARKS:
            if idx in landmarks:
                xs.append(landmarks[idx][0])

        if xs:
            left = min(xs)
            right = max(xs)
            box = Box(
                x=min(box.left, left),
                y=box.y,
                w=max(box.right, right) - min(box.left, left),
                h=box.h,
            )

    box = box.apply_padding(BOX_RULES["upper_body"]["padding"])
    
    if landmarks and "image_w" in landmarks:
        box = box.clamp(
        landmarks["image_w"],
        landmarks["image_h"],
    )
    
    return box