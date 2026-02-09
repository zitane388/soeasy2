# gui/product_detail/thumb_panel_extensions/discover.py

import pkgutil
import importlib
import sys
from .base import UI_EXTENSIONS

_DISCOVERED = False

def discover_extensions(item):
    """
    ThumbnailPanel에서 호출됨. 
    1) 모듈 스캔 (최초 1회)
    2) 아이템 조건 체크 후 빌더 리스트 반환
    """
    global _DISCOVERED

    # --- 1. 모듈 자동 스캔 (Registration) ---
    if not _DISCOVERED:
        package_name = __package__ or "gui.product_detail.thumb_panel_extensions"
        try:
            # 현재 패키지 내의 모듈들을 임포트하여 데코레이터(@register_ui_extension) 실행
            package = sys.modules[package_name]
            for _, module_name, _ in pkgutil.iter_modules(package.__path__):
                if module_name not in ["base", "discover"]:
                    full_module_name = f"{package_name}.{module_name}"
                    importlib.import_module(full_module_name)
                    print(f"[UI_DISCOVER] Loaded module: {full_module_name}")
            _DISCOVERED = True
        except Exception as e:
            print(f"[UI_DISCOVER] Scan Error: {e}")

    # --- 2. 아이템에 맞는 UI 필터링 ---
    applicable = []
    for ext_func in UI_EXTENSIONS:
        try:
            # ext_func는 @register_ui_extension이 붙은 함수(예: extra_option)
            info = ext_func(item) # 여기서 item 전달
            if info:
                applicable.append(info)
        except Exception as e:
            print(f"[UI_DISCOVER] Call Error in {ext_func.__name__}: {e}")

    return applicable