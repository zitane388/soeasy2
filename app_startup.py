import os
import shutil
import torch
from rembg import new_session
from utils.path import p

BASE_DIR = p()

def clear_temp_dir(path: str):
    if not os.path.exists(path):
        return
    for name in os.listdir(path):
        full = os.path.join(path, name)
        try:
            if os.path.isfile(full) or os.path.islink(full):
                os.remove(full)
            elif os.path.isdir(full):
                shutil.rmtree(full)
        except Exception as e:
            print(f"[TEMP CLEAN WARN] {full} 삭제 실패:", e)

# ------------------------------------------------------
# 1) TEMP 정리 (앱 시작 시 1회)
# ------------------------------------------------------
clear_temp_dir(p("windly_temp"))
clear_temp_dir(p("image_tools", "temp_img"))
print("[TEMP] cleaned")

# ------------------------------------------------------
# 2) torch.load 패치 (BiRefNet용)
# ------------------------------------------------------
_original_torch_load = torch.load

def patched_torch_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return _original_torch_load(*args, **kwargs)

torch.load = patched_torch_load

# ------------------------------------------------------
# 3) 세그멘테이션 세션 로딩 (실사용 모델만)
# ------------------------------------------------------
SESSION = new_session("birefnet-portrait")

print("[MODEL] Ready (BiRefNet only)")