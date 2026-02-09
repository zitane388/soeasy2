# image_tools/thumbnail_config.py

from dataclasses import dataclass

@dataclass
class ThumbnailConfig:
    template: str                 # "상의 1명", "하의 1명 + 제품 1개"
    image_urls: list[str]          # 슬롯에서 선택된 URL
    ext_state: dict                # 확장 옵션 상태
