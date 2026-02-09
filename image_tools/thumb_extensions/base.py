# 이미지 확장용 레지스트리
THUMB_EXTENSIONS = []

def register_thumbnail_extension(func):
    """이미지 후처리 확장 모듈 등록"""
    THUMB_EXTENSIONS.append(func)
    return func
