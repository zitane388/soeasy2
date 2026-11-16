from PIL import Image
import logging

log = logging.getLogger("thumbnail_engine")

class OverlapDoubleLayout:
    # image_count 인자를 추가합니다 (기본값 3)
    def get_slots_info(self, canvas_size=(1000, 1000), overlap_ratio: float = 0.2, image_count=3):
        canvas_w, canvas_h = canvas_size
        """
        메인(70%)과 서브 2개(40%)의 슬롯 정보를 반환합니다.
        서브 상품 2개는 서로 세로로 살짝 겹치며(Overlap), 
        그 뭉치 전체가 캔버스의 세로 중앙에 위치합니다.
        """
        canvas_w, canvas_h = canvas_size
        
        # 1. 가로 영역 (메인 70%, 서브 40% -> 10% 가로 중첩)
        main_w = int(canvas_w * 0.7)
        right_w = int(canvas_w * 0.4)
        right_x = canvas_w - right_w

        # 2. 세로 영역 (서브 2개 중첩 및 중앙 정렬)
        # 서브 개별 높이는 캔버스의 절반으로 설정
        base_slot_h = canvas_h // 2
        # overlap_ratio만큼 겹치게 배치하기 위한 이동 간격(step)
        step = int(base_slot_h * (1 - overlap_ratio))
        
        # 서브 뭉치 전체의 높이: 첫 번째 슬롯의 노출부(step) + 두 번째 슬롯 전체(base_slot_h)
        stack_h = step + base_slot_h
        
        # 서브 뭉치를 세로 중앙에 놓기 위한 시작점
        start_y = (canvas_h - stack_h) // 2

        slots = [
            {
                "size": (main_w, canvas_h), 
                "pos": (0, 0)
            },
            {
                "size": (right_w, base_slot_h), 
                "pos": (right_x, start_y)
            },
            {
                "size": (right_w, base_slot_h), 
                "pos": (right_x, start_y + step) # 첫 번째 서브 위로 살짝 겹쳐짐
            }
        ]
        return slots

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
        overlap_ratio: float = 0.2,
    ) -> Image.Image:
        if len(images) != 3:
            raise ValueError("OverlapDoubleLayout requires 3 images (main + 2 subs)")

        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        slots = self.get_slots_info(canvas_size, overlap_ratio=overlap_ratio)

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            temp.paste(img_rgba, slot["pos"])
            # alpha_composite로 겹친 부분의 테두리를 깨끗하게 처리
            canvas = Image.alpha_composite(canvas, temp)

        if to_rgb:
            from .utils import paste_on_prebuilt_bg
            return paste_on_prebuilt_bg(canvas)

        return canvas