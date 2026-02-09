# main.py
import threading, os, sys, shutil

from utils.path import p  # ← get_base_dir / p 정의된 공통 유틸이라고 가정

from html_receiver import run_html_receiver
from gui.main_window import run_gui
from app_startup import SESSION


# ---------------------------------------------------------
def main():

    # HTML 수신 서버 실행
    server_thread = threading.Thread(target=run_html_receiver, daemon=True)
    server_thread.start()

    # Windly Temp 폴더 생성 (실행파일 기준)
    WINDLY_TEMP_ROOT = p("windly_temp")
    os.makedirs(WINDLY_TEMP_ROOT, exist_ok=True)

    # GUI 실행
    run_gui()


# ---------------------------------------------------------
if __name__ == "__main__":
    main()
