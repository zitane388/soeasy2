# main.py
import threading, os
from html_receiver import run_html_receiver
from gui import run_gui

def main():
    # 1) HTML 수신 서버 실행
    server_thread = threading.Thread(target=run_html_receiver, daemon=True)
    server_thread.start()
    
    WINDLY_TEMP_ROOT = r"C:/soeasy2/windly_temp"

    if not os.path.exists(WINDLY_TEMP_ROOT):
        os.makedirs(WINDLY_TEMP_ROOT)

    # 2) GUI 실행
    run_gui()


if __name__ == "__main__":
    main()
