import os
from PIL import Image
import logging

log = logging.getLogger("thumbnail_engine")

# 실제 최종 배경색 (회색선 방지의 핵심 컬러)
TARGET_BG_RGB = (243, 243, 243)

def resize_aspect_fit(img: Image.Image, target_w: int, target_h: int):
    """
    비율을 유지하며 리사이즈합니다. 
    리사이즈 시 발생하는 회색 윤곽선을 방지하기 위해 '회색 투명' 캔버스를 사용합니다.
    """
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    iw, ih = img.size
    scale = min(target_w / iw, target_h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))

    # 1. 리사이즈 (LANCZOS 유지)
    resized = img.resize((nw, nh), Image.LANCZOS)

    # 2. [핵심] 배경색과 동일한 RGB를 가진 '투명' 캔버스 생성 (243, 243, 243, 0)
    # 주변 픽셀이 섞여도 검은색이 아닌 타겟 배경색이 섞이게 하여 테두리 오염을 막습니다.
    transparent_gray = (*TARGET_BG_RGB, 0)
    canvas = Image.new("RGBA", (target_w, target_h), transparent_gray)
    
    x = (target_w - nw) // 2
    y = (target_h - nh) // 2

    # 3. 부드러운 합성을 위한 alpha_composite
    tmp = Image.new("RGBA", (target_w, target_h), transparent_gray)
    tmp.paste(resized, (x, y))
    
    return Image.alpha_composite(canvas, tmp)


def paste_on_prebuilt_bg(fg_rgba: Image.Image, pos=(0, 0)):
    """
    레이아웃 작업이 완료된 투명 이미지를 최종 배경색(243, 243, 243) 위에 합성합니다.
    """
    if fg_rgba.mode != "RGBA":
        fg_rgba = fg_rgba.convert("RGBA")

    # 1. 최종 결과 배경색 (완전 불투명 회색)
    bg = Image.new("RGBA", fg_rgba.size, (*TARGET_BG_RGB, 255))
    
    # 2. 섞여도 티 나지 않도록 '회색 투명' 레이어 생성
    overlay = Image.new("RGBA", bg.size, (*TARGET_BG_RGB, 0))
    overlay.paste(fg_rgba, pos)
    
    # 3. 알파 블렌딩 후 최종 RGB 변환 (JPG 저장 등을 위해)
    # 이 과정에서 외곽선이 배경색과 자연스럽게 녹아듭니다.
    result = Image.alpha_composite(bg, overlay)
    return result.convert("RGB")