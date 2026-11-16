import re
from urllib.parse import urlparse


def analyze_video_url(video_url: str):
    """
    video_url을 분석해 포맷/재생 가능 여부/변환 필요 여부를 판단.
    반환 형식:
    {
        "format": str,
        "playable": bool,
        "needs_convert": bool,
        "safe_url": str,
    }
    """

    if not video_url or not isinstance(video_url, str):
        return {
            "format": None,
            "playable": False,
            "needs_convert": False,
            "safe_url": None,
        }

    url_lower = video_url.lower()

    # --------------------------
    # 1) mp4
    # --------------------------
    if ".mp4" in url_lower:
        return {
            "format": "mp4",
            "playable": True,          # HTML5 video 바로 재생
            "needs_convert": False,
            "safe_url": video_url,
        }

    # --------------------------
    # 2) HLS (m3u8)
    # --------------------------
    if url_lower.endswith(".m3u8") or "m3u8" in url_lower:
        return {
            "format": "m3u8",
            "playable": False,         # HTML5 단독에서는 재생불가
            "needs_convert": True,     # mp4 변환 가능
            "safe_url": None,
        }

    # --------------------------
    # 3) DASH (mpd)
    # --------------------------
    if url_lower.endswith(".mpd"):
        return {
            "format": "mpd",
            "playable": False,
            "needs_convert": True,     # mp4 변환 필요
            "safe_url": None,
        }

    # --------------------------
    # 4) blob URL
    # --------------------------
    if url_lower.startswith("blob:"):
        return {
            "format": "blob",
            "playable": False,
            "needs_convert": False,    # 원본 URL로 직접 변환 불가
            "safe_url": None,
        }

    # --------------------------
    # 5) iframe/embed URL
    # --------------------------
    if "iframe" in url_lower or "embed" in url_lower:
        return {
            "format": "iframe",
            "playable": False,         # <video> 불가능
            "needs_convert": False,
            "safe_url": video_url,     # iframe 삽입은 가능
        }

    # --------------------------
    # 6) webm
    # --------------------------
    if url_lower.endswith(".webm"):
        return {
            "format": "webm",
            "playable": True,          # 대부분 브라우저 재생 가능 (하지만 상점마다 제한 있음)
            "needs_convert": False,
            "safe_url": video_url,
        }

    # --------------------------
    # 7) 기타 (알 수 없는 형식)
    # --------------------------
    return {
        "format": "unknown",
        "playable": False,
        "needs_convert": False,
        "safe_url": video_url,
    }

import re
import subprocess
import requests
import os
from urllib.parse import urljoin
from automation.windly_config_loader import get_windly_temp_dir

OUTPUT_NAME = "video.mp4"     # 항상 고정 (덮어쓰기)
_last_video_url = None  # 마지막 다운로드한 URL 저장

def download_and_convert_video(raw_url):
    """
    유니클로 subvideo(HLS disguised mp4)를 받아
    최고 해상도 m3u8 → mp4 파일로 변환하여
    windly_temp/video.mp4 로 저장 (항상 덮어쓰기)

    반환: mp4 절대경로 또는 None
    """

    try:
        # windly_temp 경로 공통 관리
        global _last_video_url
        WINDLY_TEMP = get_windly_temp_dir()
        output_path = os.path.join(WINDLY_TEMP, OUTPUT_NAME)
        
        # 캐시 확인: 이미 같은 URL로 다운로드한 경우
        if _last_video_url == raw_url and os.path.exists(output_path):
            return output_path

        # 기존 파일 삭제 (덮어쓰기 보장)
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.uniqlo.com/",
        }

        # 1) Master playlist 받아오기
        resp = requests.get(raw_url, headers=headers, allow_redirects=True, timeout=15)
        master_m3u8 = resp.text

        # 2) Base URL
        base_url = raw_url.split("?")[0].rsplit("/", 1)[0] + "/"

        # 3) variant m3u8 리스트
        variant_files = re.findall(r'([a-zA-Z0-9._-]+_([0-9]+)\.m3u8)', master_m3u8)
        if not variant_files:
            print("❌ variant m3u8 찾기 실패")
            return None

        # 가장 높은 해상도 선택
        best_quality = sorted(variant_files, key=lambda x: int(x[1]))[-1][0]
        best_m3u8_url = urljoin(base_url, best_quality)

        # 4) ffmpeg 다운로드
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite
            "-headers",
            "Referer: https://www.uniqlo.com/\r\nUser-Agent: Mozilla/5.0\r\n",
            "-i",
            best_m3u8_url,
            "-c",
            "copy",
            output_path,
        ]

        subprocess.run(cmd, check=True)

        return output_path

    except Exception as e:
        print("❌ 영상 변환 실패:", e)
        return None