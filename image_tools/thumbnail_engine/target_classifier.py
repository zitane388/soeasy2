# image_tools/thumbnail_engine/target_classifier.py

from .logger import get_logger

log = get_logger()

POSE_LANDMARKS = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}

def _has_any(landmarks: dict, keys: list[int]) -> bool:
    return any(k in landmarks for k in keys)


def auto_classify_target_type(landmarks: dict) -> str:
    has_ankle = _has_any(
        landmarks,
        [POSE_LANDMARKS["left_ankle"], POSE_LANDMARKS["right_ankle"]],
    )
    has_knee = _has_any(
        landmarks,
        [POSE_LANDMARKS["left_knee"], POSE_LANDMARKS["right_knee"]],
    )
    has_hip = _has_any(
        landmarks,
        [POSE_LANDMARKS["left_hip"], POSE_LANDMARKS["right_hip"]],
    )
    has_shoulder = _has_any(
        landmarks,
        [POSE_LANDMARKS["left_shoulder"], POSE_LANDMARKS["right_shoulder"]],
    )

    log.debug(
        "auto classify landmarks shoulder=%s hip=%s knee=%s ankle=%s",
        has_shoulder, has_hip, has_knee, has_ankle,
    )

    # 1️⃣ 발목 → 무조건 전신
    if has_ankle:
        log.info("target classified as full_body (ankle detected)")
        return "full_body"

    # 2️⃣ 하체가 더 명확하면 lower_body 우선
    if has_hip and has_knee and not has_shoulder:
        log.info("target classified as lower_body (hip+knee detected)")
        return "lower_body"

    # 3️⃣ 상체
    if has_shoulder and has_hip:
        log.info("target classified as upper_body (shoulder+hip detected)")
        return "upper_body"

    log.warning("target classified fallback=upper_body")
    return "upper_body"
