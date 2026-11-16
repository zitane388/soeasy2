# browser_launcher.py
import os
import subprocess
import logging
import webbrowser

def open_in_chrome(url: str):
    """설치된 Chrome을 찾아서 해당 URL을 띄운다 (확장프로그램 활성 프로필 유지)."""

    chrome_paths = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        # Windows
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]

    chrome_path = next((p for p in chrome_paths if os.path.exists(p)), None)

    if chrome_path:
        subprocess.Popen([chrome_path, url])
    else:
        logging.warning("[CHROME] Chrome 실행파일을 찾을 수 없어 기본 브라우저로 엽니다.")
        webbrowser.open(url)
