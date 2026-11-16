# configs/image_settings.py

HTTP2_REQUIRED_DOMAINS = [
    "muji.com",
]

COMMON_IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.muji.com/jp/ja/",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "ja-JP,ja;q=0.9,ko-KR;q=0.8,en-US;q=0.6",
}