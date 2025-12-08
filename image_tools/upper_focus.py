# upper_focus.py
# "상의 1명" 템플릿 전용 — 얼굴 반만 보이고, 상의는 절대 잘리지 않으며 최종 1000×1000 출력
# GUI에서 1장만 선택됐을 때 호출할 수 있도록 함수화 완료

import cv2
import mediapipe as mp
import numpy as np
from PIL import Image
import os, time, io, requests
from datetime import datetime


# ============================================================
# 핵심 실행 함수 (GUI는 이 함수만 호출하면 됨)
# ============================================================
def generate_upper_thumbnail(src_path, output_path=None):
    try:
        if not os.path.exists(src_path):
            return False, f"이미지를 찾을 수 없습니다: {src_path}"

        OUT_DIR = "temp_img"
        os.makedirs(OUT_DIR, exist_ok=True)

        if output_path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"{OUT_DIR}/upper_{ts}.png"

        # =====================================================
        # 실행 원본 — 얼굴 절반 + 상의 100% + 1000×1000 정사각
        # =====================================================
        FINAL = 1000

        mp_face = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.6
        )
        mp_pose = mp.solutions.pose.Pose(static_image_mode=True)

        img = cv2.imread(src_path)
        h, w = img.shape[:2]
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # 얼굴 half detect
        detection = mp_face.process(rgb).detections
        if not detection:
            return False, "얼굴을 찾을 수 없습니다"

        face = detection[0].location_data.relative_bounding_box
        fx1 = int(face.xmin * w)
        fy1 = int(face.ymin * h)
        fy2 = int((face.ymin + face.height) * h)

        face_mid = fy1 + (fy2 - fy1) // 2  # 얼굴 절반만 유지 기준

        # Pose 기반 상의 감지
        pose = mp_pose.process(rgb)
        if not pose.pose_landmarks:
            return False, "신체 랜드마크 인식 실패"

        lm = pose.pose_landmarks.landmark
        ls, rs = lm[11], lm[12]  # 어깨
        lh, rh = lm[23], lm[24]  # 골반

        shoulder_left  = int(min(ls.x, rs.x) * w)
        shoulder_right = int(max(ls.x, rs.x) * w)
        pad = int((shoulder_right - shoulder_left) * 0.25)

        sx1 = max(0, shoulder_left - pad)
        sx2 = min(w, shoulder_right + pad)

        sy_top = face_mid
        sy_bottom = int(min(lh.y, rh.y) * h)
        sy_bottom += int((sy_bottom - sy_top) * 0.25)
        sy_bottom = min(h, sy_bottom)

        # scaling → 상의 100% 보이도록 계산
        upper_h = sy_bottom - sy_top
        scale = FINAL / upper_h
        new_w, new_h = int(w*scale), int(h*scale)
        resized = cv2.resize(img, (new_w,new_h), interpolation=cv2.INTER_LANCZOS4)

        sy1 = int(sy_top * scale)
        sy2 = int(sy_bottom * scale)

        crop_top = max(0, sy1 - (FINAL//2 - (sy2 - sy1)//2))
        crop_bottom = crop_top + FINAL
        if crop_bottom > new_h:
            crop_bottom = new_h
            crop_top = crop_bottom - FINAL

        cx1 = max(0,(new_w - FINAL)//2)
        cx2 = cx1 + FINAL

        final = resized[crop_top:crop_bottom , cx1:cx2]
        cv2.imwrite(output_path, final)

        return True, output_path

    except Exception as e:
        return False, f"오류: {e}"


# ============================================================
# URL 입력도 지원 — 눌렀을 때 체크된 이미지 URL 1개 → 바로 처리
# ============================================================
def generate_upper_from_url(url):
    try:
        os.makedirs("temp_img", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        local = f"temp_img/upper_src_{ts}.png"

        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return False, f"이미지 다운로드 실패({r.status_code})"
        with open(local,"wb") as f: f.write(r.content)

        return generate_upper_thumbnail(local)

    except Exception as e:
        return False, f"[URL FAIL] {e}"
