import cv2
from pathlib import Path
from PIL import Image
import logging

# Pipeline 및 레이아웃 엔진 임포트
from image_tools.thumbnail_engine.pipeline import ThumbnailPipeline
from image_tools.thumbnail_engine.layout.overlap_triple_layout import OverlapTripleLayout
from image_tools.thumbnail_engine.layout.overlap_double_layout import OverlapDoubleLayout
from image_tools.thumbnail_engine.layout.horizontal_slot_layout import HorizontalSlotLayout
from image_tools.thumbnail_engine.layout.vertical_slot_layout import VerticalSlotLayout

log = logging.getLogger("thumbnail_engine")

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
OUT_DIR = BASE_DIR / "outputs"

ASSET_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

PRODUCT_IMG = ASSET_DIR / "test_product.jpg"
PERSON_IMG = ASSET_DIR / "test_person.jpg"

# 파이프라인 초기화
pipe = ThumbnailPipeline()

def save(img: Image.Image, name: str):
    path = OUT_DIR / name
    img.save(path)
    print(f"[SAVED] {path}")

# ==================================================
# 핵심 공통 로직: 인자 순서와 구조를 바로잡음
# ==================================================
def process_with_layout(build_func, image_paths, layout_class, target_type=None, box_rule_key=None, canvas_size=(1000, 1000)):
    # 1. 레이아웃 인스턴스 생성 및 슬롯 정보 획득
    layout = layout_class()
    image_count = len(image_paths)
    slots = layout.get_slots_info(canvas_size=canvas_size, image_count=image_count)
    
    processed_images = []
    for i, path in enumerate(image_paths):
        # 2. 파이프라인 빌드 함수 호출 (슬롯 크기 주입)
        img = build_func(
            image_path=path,
            target_type=target_type,
            box_rule_key=box_rule_key,
            override_size=slots[i]["size"], # 이제 인덱스가 정확히 일치함
            transparent=True
        )
        processed_images.append(img)
    
    # 3. 레이아웃 적용 및 최종 배경 합성
    return layout.apply(processed_images, canvas_size=canvas_size, to_rgb=True)

# --------------------------------------------------
# Test Cases
# --------------------------------------------------

def test_upper_body():
    # 파라미터 순서: (함수, 경로리스트, 레이아웃클래스, 타겟타입)
    final = process_with_layout(pipe.build_person_thumbnail, [str(PERSON_IMG)], VerticalSlotLayout, target_type="upper_body")
    save(final, "person_upper_body.png")

def test_lower_body():
    final = process_with_layout(pipe.build_person_thumbnail, [str(PERSON_IMG)], VerticalSlotLayout, target_type="lower_body")
    save(final, "person_lower_body.png")

def test_full_body():
    final = process_with_layout(pipe.build_person_thumbnail, [str(PERSON_IMG)], VerticalSlotLayout, target_type="full_body")
    save(final, "person_full_body.png")

def test_two_full_body():
    # 2개 이미지 -> HorizontalSlotLayout
    final = process_with_layout(pipe.build_person_thumbnail, [str(PERSON_IMG)] * 2, HorizontalSlotLayout, target_type="full_body")
    save(final, "two_full_body.png")
    
def test_two_upper_body():
    # 2명 상체 → 좌우 배치
    final = process_with_layout(
        pipe.build_person_thumbnail,
        [str(PERSON_IMG)] * 2,
        HorizontalSlotLayout,
        target_type="upper_body",
        box_rule_key="upper_body_tight"
        
    )
    save(final, "two_upper_body.png")
    
def test_two_lower_body():
    # 2명 하체 → 좌우 배치
    final = process_with_layout(
        pipe.build_person_thumbnail,
        [str(PERSON_IMG)] * 2,
        HorizontalSlotLayout,
        target_type="lower_body",
        box_rule_key="lower_body_loose"
    )
    save(final, "two_lower_body.png")

def test_product_single():
    final = process_with_layout(pipe.build_product_thumbnail, [str(PRODUCT_IMG)], VerticalSlotLayout)
    save(final, "product_single.png")

def test_overlap_double_product():
    # 3개 이미지 -> OverlapDoubleLayout
    final = process_with_layout(pipe.build_product_thumbnail, [str(PRODUCT_IMG)] * 3, OverlapDoubleLayout)
    save(final, "product_overlap_double.png")

def test_overlap_triple_product():
    # 4개 이미지 (메인1+서브3) -> OverlapTripleLayout
    final = process_with_layout(pipe.build_product_thumbnail, [str(PRODUCT_IMG)] * 4, OverlapTripleLayout)
    save(final, "product_overlap_triple.png")

if __name__ == "__main__":
    # test_upper_body()
    # test_lower_body()
    # test_full_body()
    # test_two_full_body()
    # test_two_upper_body()
    # test_two_lower_body()
    test_product_single()
    test_overlap_double_product()
    test_overlap_triple_product()