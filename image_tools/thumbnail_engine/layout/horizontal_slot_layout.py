from PIL import Image
import logging

log = logging.getLogger("thumbnail_engine")

class HorizontalSlotLayout:
    def get_slots_info(self, canvas_size=(1000, 1000), image_count=1):
        """
        파이프라인이 이미지를 생성하기 전에 각 슬롯의 정확한 가로폭과 위치를 반환합니다.
        가로로 n등분하는 레이아웃입니다.
        """
        if image_count <= 0:
            raise ValueError("image_count must be at least 1")

        canvas_w, canvas_h = canvas_size
        slot_w = canvas_w // image_count
        
        slots = []
        for i in range(image_count):
            # 마지막 슬롯은 정수 나눗셈 오차를 보정하기 위해 남은 폭을 모두 할당
            current_w = slot_w if i < image_count - 1 else canvas_w - (slot_w * i)
            
            slots.append({
                "size": (current_w, canvas_h), # 렌더러가 생성해야 할 이미지 크기
                "pos": (slot_w * i, 0)          # 캔버스에 배치될 좌표
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
        if not images:
            raise ValueError("HorizontalSlotLayout requires at least 1 image")

        canvas_w, canvas_h = canvas_size
        # 1. 완전 투명한 기반 캔버스 생성
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        # 2. 슬롯 정보 기반으로 배치
        slots = self.get_slots_info(canvas_size, image_count=len(images))

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            
            # 리사이즈 로직 제거: 이미 Renderer에서 slot["size"]에 맞춰 생성됨
            # alpha_composite를 위해 동일 크기의 임시 캔버스 사용
            temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            temp.paste(img_rgba, slot["pos"])
            
            # 수학적으로 정확한 알파 합성을 위해 alpha_composite 사용
            canvas = Image.alpha_composite(canvas, temp)

        # 3. 최종 배경 합성 (to_rgb가 True인 경우 utils 사용)
        if to_rgb:
            from .utils import paste_on_prebuilt_bg
            # 회색 투명 전략이 포함된 utils 함수 호출
            return paste_on_prebuilt_bg(canvas)

        return canvas