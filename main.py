# main.py
import threading
from html_receiver import run_html_receiver
from gui import run_gui

def main():
    # 1) HTML 수신 서버 실행
    server_thread = threading.Thread(target=run_html_receiver, daemon=True)
    server_thread.start()

    # 2) GUI 실행
    run_gui()


if __name__ == "__main__":
    main()
