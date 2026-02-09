# image_tools/thumbnail_extensions/registry.py
"""
thumbnail extension pipeline

- 모든 썸네일 확장(ext)은 이 파이프라인을 통해 적용한다.
- 현재 일부 호출부에서는 직접 ext를 호출할 수 있으나,
  최종적으로는 apply_thumbnail_extensions()로 통합할 예정.
"""
from .color_strip_overlay_ext import color_strip_ext

THUMB_EXTENSIONS = [
    color_strip_ext,
]

def apply_thumbnail_extensions(item, img, ext_state):
    print("\n==========================")
    print("[THUMB_EXT] START EXTENSIONS")
    print(f"brand={item.brand}, country={item.country}, ext_state={ext_state}")
    print("==========================")

    for ext in THUMB_EXTENSIONS:
        print(f"[THUMB_EXT] → Running extension: {ext.__name__}")

        try:
            new_img = ext(item=item, img=img, ext_state=ext_state)

            if new_img is None:
                print(f"[THUMB_EXT]   {ext.__name__} returned None (skip)")
            else:
                print(f"[THUMB_EXT]   {ext.__name__} applied OK")
                img = new_img

        except Exception as e:
            print(f"[THUMB_EXT] !! ERROR in {ext.__name__}: {e}")

    print("[THUMB_EXT] END EXTENSIONS")
    print("==========================\n")
    return img
