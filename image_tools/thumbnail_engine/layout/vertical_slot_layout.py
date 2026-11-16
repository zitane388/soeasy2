from PIL import Image
import logging

log = logging.getLogger("thumbnail_engine")

class VerticalSlotLayout:
    def get_slots_info(self, canvas_size=(1000, 1000), image_count=1):
        """
        파이프라인이 이미지를 생성하기 전에 각 슬롯의 정확한 규격과 위치를 반환합니다.
        세로로 n등분하는 레이아웃입니다.
        """
        canvas_w, canvas_h = canvas_size
        slot_h = canvas_h // image_count
        
        slots = []
        for i in range(image_count):
            slots.append({
                "size": (canvas_w, slot_h),  # 렌더러가 생성해야 할 이미지 크기
                "pos": (0, i * slot_h)       # 캔버스에 배치될 좌표
            })
        return slots

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
    ) -> Image.Image:
        """
        이미 렌더러에서 슬롯 사이즈에 맞춰 생산된 이미지들을 받아 최종 캔버스에 합성합니다.
        """
        canvas_w, canvas_h = canvas_size
        # 1. 완전 투명한 기반 캔버스 생성
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        # 2. 슬롯 정보 기반으로 배치
        # images의 개수에 맞춰 슬롯 정보를 다시 가져옵니다.
        slots = self.get_slots_info(canvas_size, image_count=len(images))

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            
            # 리사이즈 로직 없음: 이미 Renderer에서 slot["size"]에 맞춰 생성됨
            # alpha_composite를 사용해 투명도가 있는 상태로 부드럽게 얹음
            temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            temp.paste(img_rgba, slot["pos"])
            canvas = Image.alpha_composite(canvas, temp)

        # 3. 최종 배경 합성 (to_rgb가 True인 경우)
        if to_rgb:
            from .utils import paste_on_prebuilt_bg
            # 미리 정의된 배경(243, 243, 243) 위에 투명 캔버스를 얹음
            return paste_on_prebuilt_bg(canvas)

        return canvas