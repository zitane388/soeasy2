# config/smartstore_config.py

import os
from dotenv import load_dotenv

load_dotenv()

def load_smartstore_config():
    """
    SmartStore 로그인 정보
    - .env 파일에서 환경변수 로드
    """
    naver_id = os.getenv("NAVER_ID")
    naver_pw = os.getenv("NAVER_PW")

    if not naver_id or not naver_pw:
        raise RuntimeError(
            "환경변수 NAVER_ID, NAVER_PW가 설정되지 않았습니다.\n"
            ".env 파일에 네이버 계정 정보를 설정해주세요."
        )

    return {
        "naver_id": naver_id,
        "naver_pw": naver_pw,
        "headless": False,
    }
