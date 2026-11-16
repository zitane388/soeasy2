# windly_config_loader.py
import os
from dotenv import load_dotenv
from utils.path import p

load_dotenv()

# ------------------------------------------
# 기본 경로 설정
# ------------------------------------------

# Windly 전용 임시폴더 (영상, 옵션/사이즈 이미지 등 저장)
WINDLY_TEMP_DIR = p("windly_temp")

# ------------------------------------------
# Windly 계정 정보 로드
# ------------------------------------------

def load_windly_config():
    """
    .env 파일에서 WINDLY_USER_ID / WINDLY_USER_PW를 읽는다.
    """
    user_id = os.getenv("WINDLY_USER_ID")
    user_pw = os.getenv("WINDLY_USER_PW")

    if not user_id or not user_pw:
        raise RuntimeError(
            "환경변수 WINDLY_USER_ID, WINDLY_USER_PW가 설정되지 않았습니다.\n"
            ".env 파일에 Windly 계정 정보를 설정해주세요."
        )

    return user_id, user_pw

# ------------------------------------------
# Windly temp 디렉토리 반환 (중앙 관리)
# ------------------------------------------

def get_windly_temp_dir():
    """
    Soeasy2 전체에서 사용하는 windly_temp 폴더의 절대경로 반환.
    폴더가 없으면 자동 생성.

    영상 다운로드, 옵션표 PNG, 사이즈표 PNG 등은
    모두 이 폴더 아래에서만 저장/관리된다.
    """
    os.makedirs(WINDLY_TEMP_DIR, exist_ok=True)
    return WINDLY_TEMP_DIR
