import re
import subprocess
import requests
from urllib.parse import urljoin

raw_url = "https://image.uniqlo.com/UQ/ST3/jp/imagesgoods/479669/subvideo/jpgoods_479669_sub13_video_3x4.mp4?resolution=598&streamType=hls"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.uniqlo.com/",
}

# 1) 요청 (redirect 포함)
resp = requests.get(raw_url, headers=headers, allow_redirects=True)
master_m3u8 = resp.text

# 2) base URL 추출
# raw_url에서 파일명을 제거한 디렉토리 경로로 처리
base_url = raw_url.split("?")[0].rsplit("/", 1)[0] + "/"

print("▶ base URL:", base_url)

# 3) 마스터 m3u8에서 해상도별 m3u8 리스트 추출
variant_files = re.findall(r'([a-zA-Z0-9._-]+_([0-9]+)\.m3u8)', master_m3u8)

if not variant_files:
    print("❌ variant m3u8 파일을 찾지 못했습니다.")
    print(master_m3u8[:300])
    raise SystemExit()

# 가장 고해상도(1080) 선택
best_quality = sorted(variant_files, key=lambda x: int(x[1]))[-1][0]
best_m3u8_url = urljoin(base_url, best_quality)

print("▶ 선택된 최고 해상도 m3u8:", best_m3u8_url)

# 4) ffmpeg 다운로드
cmd = [
    "ffmpeg",
    "-headers",
    "Referer: https://www.uniqlo.com/\r\nUser-Agent: Mozilla/5.0\r\n",
    "-i",
    best_m3u8_url,
    "-c",
    "copy",
    "uniqlo_video.mp4",
]

print("\n▶ FFmpeg 다운로드 시작...\n")
subprocess.run(cmd, check=True)

print("🎉 다운로드 완료: uniqlo_video.mp4")
