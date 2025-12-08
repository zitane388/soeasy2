# main.py
import threading, os, sys, shutil, glob
from html_receiver import run_html_receiver
from gui import run_gui

from app_startup import SESSION, YOLO_MODEL


# ---------------------------------------------------------
#  PyInstaller onefile 실행 시 내부 리소스 + bcrypt DLL 추출
# ---------------------------------------------------------
def extract_resources():
    if not getattr(sys, 'frozen', False):
        return  # 개발환경에서는 패스

    base = sys._MEIPASS                # PyInstaller 내부 가상 폴더
    exe_dir = os.path.dirname(sys.executable)

    folders = [
        "automation",
        "data",
        "llm",
        "rules",
        "parsers",
        "utils",
        "naver_uploader",
        "templates",
        "images",
        "windly_temp",
        "scrapers"
    ]

    # 일반 리소스 폴더 복사
    for name in folders:
        src = os.path.join(base, name)
        dst = os.path.join(exe_dir, name)

        if os.path.exists(dst):
            continue

        if os.path.isdir(src):
            shutil.copytree(src, dst)
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


# ---------------------------------------------------------
def main():
    extract_resources()

    server_thread = threading.Thread(target=run_html_receiver, daemon=True)
    server_thread.start()

    WINDLY_TEMP_ROOT = r"C:/soeasy2/windly_temp"
    if not os.path.exists(WINDLY_TEMP_ROOT):
        os.makedirs(WINDLY_TEMP_ROOT)

    run_gui()


if __name__ == "__main__":
    main()
