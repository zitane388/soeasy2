# image_tools/image_utils.py
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove
import shutil
import os
from image_tools.config import TEMP_IMG_DIR

# -----------------------------------------
# temp_img 정리
# -----------------------------------------

def clean_temp_images():
    """
    TEMP_IMG_DIR 내부에서 thumbnail_*.png 를 제외한
    모든 중간 처리 파일을 삭제한다.
    즉, 각 상품의 최종 썸네일은 모두 유지한다.
    """
    print(f"[TEMP_IMG] clean_temp_images 호출, 경로: {TEMP_IMG_DIR}")

    if not os.path.exists(TEMP_IMG_DIR):
        print("[TEMP_IMG] 폴더가 존재하지 않음 → 종료")
        return

    for fname in os.listdir(TEMP_IMG_DIR):
        fpath = os.path.join(TEMP_IMG_DIR, fname)
        print(f"[TEMP_IMG] 처리 대상: {fpath}")

        # 1) 폴더면 스킵
        if os.path.isdir(fpath):
            print(f"[TEMP_IMG] 폴더 → 스킵: {fpath}")
            continue

        # 2) 최종 썸네일은 유지
        if fname.startswith("thumbnail_") and fname.endswith(".png"):
            print(f"[TEMP_IMG] 최종 썸네일 → 유지: {fpath}")
            continue

        # 3) 그 외는 모두 삭제 = 중간 파일
        try:
            os.remove(fpath)
            print(f"[TEMP_IMG] 삭제 완료: {fpath}")
        except Exception as e:
            print(f"[TEMP_IMG][ERROR] 삭제 실패: {fpath} → {e}")


def clean_temp_all():
    """
    프로그램 시작 시 호출.
    TEMP_IMG_DIR 전체 삭제 후 재생성(빈 폴더).
    """
    print(f"[TEMP_IMG] clean_temp_all 호출, 경로: {TEMP_IMG_DIR}")

    if os.path.exists(TEMP_IMG_DIR):
        print(f"[TEMP_IMG] 기존 폴더 삭제: {TEMP_IMG_DIR}")
        shutil.rmtree(TEMP_IMG_DIR)

    os.makedirs(TEMP_IMG_DIR, exist_ok=True)
    print(f"[TEMP_IMG] 폴더 생성 완료: {TEMP_IMG_DIR}")


def clean_alpha_edges(img: Image.Image) -> Image.Image:
    """
    rembg 후 남는 회색 halo 제거 + 경계 부드럽게 만들기
    """
    import cv2
    import numpy as np

    rgba = np.array(img)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]

    # 1) Canny로 경계 검출
    edges = cv2.Canny(alpha, 30, 100)
    edges = cv2.GaussianBlur(edges, (3,3), 0)

    # 2) 경계 주변 알파를 약하게 만들어 Halo 제거
    kernel = np.ones((3,3), np.uint8)
    dil = cv2.dilate(edges, kernel, iterations=2)
    alpha[dil > 0] = alpha[dil > 0] // 4

    # 3) Feather 효과 적용
    alpha = cv2.GaussianBlur(alpha, (3,3), 0)

    out = np.dstack([rgb, alpha])
    return Image.fromarray(out)
