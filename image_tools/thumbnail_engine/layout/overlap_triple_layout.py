from PIL import Image
import logging

log = logging.getLogger("thumbnail_engine")

class OverlapTripleLayout:
    # image_count 인자를 추가합니다 (기본값 4)
    def get_slots_info(self, canvas_size=(1000, 1000), overlap_ratio: float = 0.2, image_count=4):
        canvas_w, canvas_h = canvas_size
        """
        메인(70%)과 서브 3개(40%)의 슬롯 정보를 반환합니다.
        우측 서브 상품 3개는 서로 세로로 살짝 겹치며, 
        그 뭉치 전체가 캔버스의 세로 중앙에 위치합니다.
        """
        canvas_w, canvas_h = canvas_size
        
        # 1. 가로 영역 (메인 70%, 서브 40% -> 10% 가로 중첩)
        main_w = int(canvas_w * 0.7)
        right_w = int(canvas_w * 0.4)
        right_x = canvas_w - right_w

        # 2. 세로 영역 (서브 3개 중첩 및 중앙 정렬)
        # 서브 개별 높이는 3분할 수준으로 설정 (333px 정도)
        base_slot_h = canvas_h // 3
        # 이동 간격(step): 이전 슬롯의 시작점부터 다음 슬롯 시작점까지의 거리
        step = int(base_slot_h * (1 - overlap_ratio))
        
        # 서브 뭉치 전체의 높이 계산:
        # (첫 번째 노출 높이: step) + (두 번째 노출 높이: step) + (마지막 슬롯 전체: base_slot_h)
        stack_h = (step * 2) + base_slot_h
        
        # 서브 뭉치 덩어리를 세로 중앙에 배치하기 위한 시작 Y 좌표
        start_y = (canvas_h - stack_h) // 2

        # 슬롯 정의 생성
        slots = []
        # [0] 메인 슬롯
        slots.append({
            "size": (main_w, canvas_h), 
            "pos": (0, 0)
        })
        
        # [1, 2, 3] 서브 슬롯 3개
        for i in range(3):
            slots.append({
                "size": (right_w, base_slot_h),
                "pos": (right_x, start_y + (i * step))
            })
            
        return slots

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
        overlap_ratio: float = 0.2,
    ) -> Image.Image:
        """
        메인 1개와 서브 3개를 중첩 레이어링하여 최종 합성합니다.
        """
        if len(images) != 4:
            raise ValueError("OverlapTripleLayout requires 4 images (main + 3 subs)")

        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        # 중앙 정렬 및 중첩 로직이 포함된 슬롯 정보
        slots = self.get_slots_info(canvas_size, overlap_ratio=overlap_ratio)

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            temp.paste(img_rgba, slot["pos"])
            # alpha_composite로 층층이 쌓아 올림 (뒤 순서 이미지가 위로 올라옴)
            canvas = Image.alpha_composite(canvas, temp)

        # 최종 배경 합성 (utils의 회색 투명 전략 반영)
        if to_rgb:
            from .utils import paste_on_prebuilt_bg
            return paste_on_prebuilt_bg(canvas)

        return canvas