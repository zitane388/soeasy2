# image_tools/thumbnail_engine/detection/mediapipe_detector.py

import cv2
import mediapipe as mp
from ..box.base import Box
from ..box.pose_parts import (
    build_full_body_raw_box,
    build_upper_body_raw_box,
    build_lower_body_raw_box,
)
from ..logger import get_logger

log = get_logger()

mp_pose = mp.solutions.pose
mp_face = mp.solutions.face_detection


class MediaPipeDetector:
    def __init__(self):
        log.info("MediaPipeDetector init")
        self.pose = mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
        )
        self.face = mp_face.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.6,
        )

    # --------------------------------------------------
    # 얼굴 박스
    # --------------------------------------------------
    def detect_face_box(self, image_bgr):
        h, w, _ = image_bgr.shape
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        result = self.face.process(rgb)

        if not result.detections:
            log.info("face detection failed")
            return None

        det = result.detections[0]
        box = det.location_data.relative_bounding_box

        face_box = Box(
            x=box.xmin * w,
            y=box.ymin * h,
            w=box.width * w,
            h=box.height * h,
        )

        log.debug(
            "face_box detected x=%.1f y=%.1f w=%.1f h=%.1f",
            face_box.x, face_box.y, face_box.w, face_box.h,
        )

        return face_box

    # --------------------------------------------------
    # pose + raw boxes
    # --------------------------------------------------
    def detect_pose(self, image_bgr):
        h, w, _ = image_bgr.shape
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        result = self.pose.process(rgb)

        if not result.pose_landmarks:
            log.warning("pose detection failed")
            return None

        landmarks = {}
        for idx, lm in enumerate(result.pose_landmarks.landmark):
            landmarks[idx] = (lm.x * w, lm.y * h)
        
        landmarks["image_w"] = w
        landmarks["image_h"] = h

        log.info(
            "pose detected landmarks_count=%d",
            len(landmarks),
        )

        full_box = build_full_body_raw_box(landmarks)
        upper_box = build_upper_body_raw_box(landmarks)
        lower_box = build_lower_body_raw_box(landmarks)

        log.debug(
            "raw pose boxes "
            "full=(%.1f,%.1f,%.1f,%.1f) "
            "upper=(%.1f,%.1f,%.1f,%.1f) "
            "lower=(%.1f,%.1f,%.1f,%.1f)",
            full_box.x, full_box.y, full_box.w, full_box.h,
            upper_box.x, upper_box.y, upper_box.w, upper_box.h,
            lower_box.x, lower_box.y, lower_box.w, lower_box.h,
        )

        return {
            "pose": full_box,
            "upper_body": upper_box,
            "lower_body": lower_box,
            "landmarks": landmarks,
        }
