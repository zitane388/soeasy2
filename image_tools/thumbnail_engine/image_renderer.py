from __future__ import annotations

import os
import numpy as np
from PIL import Image, ImageDraw
from io import BytesIO
from datetime import datetime  # <--- 누락되었던 datetime 추가
from rembg import remove

from .config import CANVAS_PRESETS
from .box.base import Box
from .logger import get_logger
from app_startup import SESSION  # pp_focus와 동일 세션 사용

log = get_logger()

# ==================================================
# DEBUG UTIL
# ==================================================
def _ensure_dir():
    os.makedirs("debug_steps", exist_ok=True)

def _save(img: Image.Image, name: str):
    _ensure_dir()
    path = os.path.join("debug_steps", f"{name}.png")
    img.save(path)
    log.info("DEBUG_SAVED %s", path)

def _dump_stage(img: Image.Image, name: str):
    os.makedirs("debug_stages", exist_ok=True)
    path = os.path.join("debug_stages", name)
    img.save(path)
    log.warning("[DUMP] %s saved (%s, %s)", path, img.size, img.mode)

# ==================================================
# rembg alpha mask apply
# ==================================================
def _apply_rembg_alpha_mask_only(final_before_rgba: Image.Image) -> Image.Image:
    if final_before_rgba.mode != "RGBA":
        final_before_rgba = final_before_rgba.convert("RGBA")

    # 1. 원본 데이터 및 rembg 결과 획득
    arr = np.array(final_before_rgba)
    # R, G, B 채널 분리
    r_chan, g_chan, b_chan = arr[:,:,0], arr[:,:,1], arr[:,:,2]

    buf = BytesIO()
    final_before_rgba.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    # rembg 실행
    removed_bytes = remove(raw_bytes, session=SESSION)
    after = Image.open(BytesIO(removed_bytes)).convert("RGBA")
    a_rembg = np.array(after)[:,:,3]

    # 2. ✨ [핵심 수정] 하단 20% 영역 강제 정화
    h, w = a_rembg.shape
    bottom_start = int(h * 0.8) # 하단 20% 지점
    
    # 원본에서 거의 흰색(230 이상)인 픽셀 마스크 생성
    # 갈색 옷은 어둡기 때문에 이 조건에 절대 걸리지 않습니다.
    bright_bg_mask = (r_chan > 230) & (g_chan > 230) & (b_chan > 230)

    # 하단부에서 '원본이 흰색인데 AI가 살려놓은 알파'를 0으로 강제 변환
    a_final = a_rembg.copy()
    a_final[bottom_start:][bright_bg_mask[bottom_start:]] = 0

    # 3. 로깅 (에러 수정된 버전)
    bottom_avg = float(a_final[bottom_start:].mean())
    log.warning(f"[REMBG-TRACE] After Clean - Bottom Alpha Avg: {bottom_avg:.2f}")

    # 4. 최종 합성 (원본 RGB + 보정된 Alpha)
    out_arr = np.stack([r_chan, g_chan, b_chan, a_final], axis=-1)
    return Image.fromarray(out_arr)

# ==================================================
# Renderer
# ==================================================
class ImageRenderer:
    def render(
        self,
        original_image: Image.Image,
        box: Box,
        pivot: tuple,
        canvas_anchor: str,
        canvas_type: str = "square",
        override_size: tuple[int, int] = None,
        background_color=(255, 255, 255),
        transparent: bool = False,
        force_remove_bg: bool = False,
        debug: bool = False,
        debug_prefix: str = "R",
        debug_run_id: str | None = None,
        target_type: str = "unknown",
    ) -> Image.Image:
        
        # 1. 캔버스 사이즈 결정
        if override_size:
            canvas_w, canvas_h = override_size
        else:
            canvas_w, canvas_h = CANVAS_PRESETS.get(canvas_type, (1000, 1000))

        # 2. 스케일 계산
        scale_w = canvas_w / box.w
        scale_h = canvas_h / box.h
        scale = min(scale_w, scale_h)

        src = original_image.convert("RGBA")
        src_w, src_h = src.size

        # 3. 리사이즈 (LANCZOS)
        new_w, new_h = int(src_w * scale), int(src_h * scale)
        scaled = src.resize((new_w, new_h), Image.LANCZOS)

        # 4. 투명 캔버스 배치
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        paste_x = int((canvas_w - box.w * scale) / 2 - box.x * scale)
        
        anchor = (canvas_anchor or "center").lower().strip()
        if anchor == "top":
            paste_y = int(-box.y * scale)
        elif anchor == "bottom":
            paste_y = int(canvas_h - (box.y + box.h) * scale)
        else:
            paste_y = int((canvas_h - box.h * scale) / 2 - box.y * scale)

        canvas.paste(scaled, (paste_x, paste_y), scaled.split()[3])

        # 5. 배경 제거 (리사이즈 직후에 마스크를 씌워 테두리 정리)
        if transparent or force_remove_bg:
            canvas = _apply_rembg_alpha_mask_only(canvas)

        # 6. 디버그 저장 (datetime 사용 부분)
        if debug:
            run_tag = debug_run_id or datetime.now().strftime("%H%M%S")
            _dump_stage(canvas, f"{debug_prefix}_{run_tag}_final_slot.png")

        return canvas