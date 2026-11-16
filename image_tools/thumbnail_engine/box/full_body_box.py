from .base import Box
from ..config import FACE_BOX_CONFIG, BOX_RULES

ARM_LANDMARKS = [11, 12, 13, 14, 15, 16]


def build_full_body_box(
    pose_box: Box,
    face_box: Box | None,
    landmarks: dict | None = None,
) -> Box:
    """
    pose_box: MediaPipe pose 전체 박스
    face_box: MediaPipe 얼굴 박스 (없을 수 있음)
    landmarks: mediapipe pose landmarks (index -> (x, y))
    """

    box = pose_box

    # --------------------------------------------------
    # 1) 얼굴 박스 보정 + pose와 merge
    #    (기존 로직 유지)
    # --------------------------------------------------
    if face_box:
        x1 = min(box.left, face_box.left)
        y1 = min(box.top, face_box.top)
        x2 = max(box.right, face_box.right)
        y2 = max(box.bottom, face_box.bottom)
        box = Box(x=x1, y=y1, w=x2 - x1, h=y2 - y1)

        # --------------------------------------------------
        # 1-2) 🔥 얼굴 "절반" 컷 (upper_body와 동일한 핵심)
        #      box.top을 face_mid로 끌어올림
        # --------------------------------------------------
        face_half_y = face_box.top + face_box.h * 0.5
        if box.top < face_half_y < box.bottom:
            box = Box(
                x=box.x,
                y=face_half_y,
                w=box.w,
                h=box.bottom - face_half_y,
            )

    # --------------------------------------------------
    # 2) 팔 포함 (좌우 확장)
    # --------------------------------------------------
    if landmarks:
        xs = []
        for idx in ARM_LANDMARKS:
            if idx in landmarks:
                x, _ = landmarks[idx]
                xs.append(x)

        if xs:
            left = min(xs)
            right = max(xs)

            x1 = min(box.left, left)
            x2 = max(box.right, right)

            box = Box(
                x=x1,
                y=box.top,
                w=x2 - x1,
                h=box.h,
            )

    # --------------------------------------------------
    # 3) 패딩
    # --------------------------------------------------
    padding = BOX_RULES["full_body"]["padding"]
    box = box.apply_padding(padding)
    
    if landmarks and "image_w" in landmarks:
        box = box.clamp(
        landmarks["image_w"],
        landmarks["image_h"],
    )

    return box
