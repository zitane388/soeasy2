# ===========================
# MODEL PRELOAD
# ===========================
print("🔵 [MODEL] Loading BiRefNet / YOLO / rembg session...")

import os
from rembg import new_session
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# rembg 모델을 "이름"이 아니라 "파일 경로"로 직접 로드하도록 수정
BIRENET_MODEL_PATH = os.path.join(BASE_DIR, "image_tools/models", "birefnet.onnx")
SESSION = new_session(model=BIRENET_MODEL_PATH)   # ← 다운로드 없음 / 로컬 실행

YOLO_MODEL_PATH = os.path.join(BASE_DIR, "image_tools/models", "yolov8x.pt")
YOLO_MODEL = YOLO(YOLO_MODEL_PATH)

print("🔵 [MODEL] Ready — BiRefNet(ONNX) + YOLO 로컬 실행")
