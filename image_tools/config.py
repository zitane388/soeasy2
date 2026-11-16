import os

# 현재 파일 기준 디렉토리 (image_tools/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# temp_img 폴더는 image_tools 안에 존재한다
TEMP_IMG_DIR = os.path.join(BASE_DIR, "temp_img")

# 폴더 생성
os.makedirs(TEMP_IMG_DIR, exist_ok=True)
