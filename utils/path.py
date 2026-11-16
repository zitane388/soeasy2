import os
import sys

import os
import sys

def get_base_dir():
    # PyInstaller로 빌드된 환경인지 확인
    if getattr(sys, 'frozen', False):
        # 1. 내부 자원(JSON, 모델 등) 경로: sys._MEIPASS
        # 2. 실행파일 위치가 필요하다면: os.path.dirname(sys.executable)
        # 보통 데이터 파일은 _MEIPASS 내부에 위치하므로 이를 우선 반환합니다.
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    
    # 개발 환경 (IDE 실행 등)
    return os.path.abspath(os.getcwd())

def p(*paths):
    return os.path.join(get_base_dir(), *paths)
