from PIL import Image
import logging

log = logging.getLogger("thumbnail_engine")


class OverlapTripleHorizontalLayout:
    """
    상의 3명 가로 배치, 중앙 이미지가 좌/우를 살짝 덮도록 구성
    """
    def get_slots_info(self, canvas_size=(1000, 1000), overlap_ratio: float = 0.12, image_count=3, center_scale: float = 1.5):
        if image_count != 3:
            raise ValueError("OverlapTripleHorizontalLayout requires 3 images")

        canvas_w, canvas_h = canvas_size
        base_w = canvas_w // 3
        overlap = int(base_w * overlap_ratio)
        center_w = int(base_w * center_scale)

        left_x = 0
        right_x = 2 * base_w
        # 중앙은 가운데 정렬 (좌우를 균등하게 덮도록)
        center_x = (canvas_w - center_w) // 2

        # 중앙이 위로 오게 좌/우/중앙 순서로 구성
        slots = [
            {"size": (base_w, canvas_h), "pos": (left_x, 0)},   # left
            {"size": (base_w, canvas_h), "pos": (right_x, 0)},  # right
            {"size": (center_w, canvas_h), "pos": (center_x, 0)},  # center (wider)
        ]
        return slots

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
        overlap_ratio: float = 0.12,
    ) -> Image.Image:
        if len(images) != 3:
            raise ValueError("OverlapTripleHorizontalLayout requires 3 images")

        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        slots = self.get_slots_info(canvas_size, overlap_ratio=overlap_ratio, image_count=3)

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            temp = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            temp.paste(img_rgba, slot["pos"])
            canvas = Image.alpha_composite(canvas, temp)

        if to_rgb:
            from .utils import paste_on_prebuilt_bg
            return paste_on_prebuilt_bg(canvas)

        return canvas
