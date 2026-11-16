# gui/product_detail/thumb_panel_extensions/__init__.py

from .base import UI_EXTENSIONS, register_ui_extension

# [중요] 실행 파일 빌드 시 누락 방지를 위해 명시적으로 임포트
try:
    from . import color_chart_extension
    print("[INIT] Extension loaded: color_chart_extension")
except Exception as e:
    print(f"[INIT] Extension load fail: {e}")

def discover_extensions(item):
    """아이템 조건에 맞는 UI 확장 리스트 반환"""
    applicable = []
    for ext_func in UI_EXTENSIONS:
        try:
            info = ext_func(item)
            if info:
                applicable.append(info)
        except Exception as e:
            print(f"[UI_DISCOVER] Error: {e}")
    return applicable