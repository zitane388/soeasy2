import json
import os

# ------------------------------------------
# 기본 경로 설정
# ------------------------------------------

# 프로젝트 루트
BASE_DIR = r"C:/soeasy2"

# Windly 전용 임시폴더 (영상, 옵션/사이즈 이미지 등 저장)
WINDLY_TEMP_DIR = os.path.join(BASE_DIR, "windly_temp")

# windly_config.json 위치
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__),
    "windly_config.json"
)

# ------------------------------------------
# Windly 계정 정보 로드
# ------------------------------------------

def load_windly_config():
    """
    windly_config.json에서 user_id / user_pw를 읽는다.
    """
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"Windly 설정 파일을 찾을 수 없습니다: {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "user_id" not in data or "user_pw" not in data:
        raise ValueError("windly_config.json 파일에 user_id, user_pw 필드가 없습니다.")

    return data["user_id"], data["user_pw"]

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
