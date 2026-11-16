from .base import Box

# MediaPipe Pose landmark index
POSE_LANDMARKS = {
    "nose": 0,

    # torso
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_hip": 23,
    "right_hip": 24,

    # arms
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,

    # legs
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


# --------------------------------------------------
# util
# --------------------------------------------------
def _bbox_from_points(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    return Box(
        x=min(xs),
        y=min(ys),
        w=max(xs) - min(xs),
        h=max(ys) - min(ys),
    )


# --------------------------------------------------
# 전신 raw box (머리~발 + 팔 전체)
# --------------------------------------------------
def build_full_body_raw_box(landmarks: dict) -> Box:
    """
    전신 박스
    - 팔, 팔꿈치, 손목 포함
    - 다리 끝까지 포함
    """
    ids = [
        # torso
        POSE_LANDMARKS["left_shoulder"],
        POSE_LANDMARKS["right_shoulder"],
        POSE_LANDMARKS["left_hip"],
        POSE_LANDMARKS["right_hip"],

        # arms
        POSE_LANDMARKS["left_elbow"],
        POSE_LANDMARKS["right_elbow"],
        POSE_LANDMARKS["left_wrist"],
        POSE_LANDMARKS["right_wrist"],

        # legs
        POSE_LANDMARKS["left_knee"],
        POSE_LANDMARKS["right_knee"],
        POSE_LANDMARKS["left_ankle"],
        POSE_LANDMARKS["right_ankle"],
    ]

    points = [landmarks[i] for i in ids if i in landmarks]
    return _bbox_from_points(points)


# --------------------------------------------------
# 상체 raw box (어깨~골반 + 팔 전체)
# --------------------------------------------------
def build_upper_body_raw_box(landmarks: dict) -> Box:
    """
    상체 박스
    - 어깨~골반
    - 팔 / 팔꿈치 / 손목까지 포함
    """
    ids = [
        # torso
        POSE_LANDMARKS["left_shoulder"],
        POSE_LANDMARKS["right_shoulder"],
        POSE_LANDMARKS["left_hip"],
        POSE_LANDMARKS["right_hip"],

        # arms
        POSE_LANDMARKS["left_elbow"],
        POSE_LANDMARKS["right_elbow"],
        POSE_LANDMARKS["left_wrist"],
        POSE_LANDMARKS["right_wrist"],
    ]

    points = [landmarks[i] for i in ids if i in landmarks]
    return _bbox_from_points(points)


# --------------------------------------------------
# 하체 raw box (골반~발)
# --------------------------------------------------
def build_lower_body_raw_box(landmarks: dict) -> Box:
    ids = [
        POSE_LANDMARKS["left_hip"],
        POSE_LANDMARKS["right_hip"],
        POSE_LANDMARKS["left_knee"],
        POSE_LANDMARKS["right_knee"],
        POSE_LANDMARKS["left_ankle"],
        POSE_LANDMARKS["right_ankle"],
    ]

    points = [landmarks[i] for i in ids if i in landmarks]
    return _bbox_from_points(points)
