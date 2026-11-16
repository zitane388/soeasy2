# UI 확장용 레지스트리
UI_EXTENSIONS = []

def register_ui_extension(func):
    """UI 확장 모듈 등록"""
    UI_EXTENSIONS.append(func)
    return func
