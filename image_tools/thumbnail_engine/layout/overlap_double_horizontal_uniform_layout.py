from PIL import Image


class OverlapDoubleHorizontalUniformLayout:
    """
    Upper-body 2-person overlap layout.
    Both subjects are widened and packed toward center with symmetric overlap.
    """

    def get_slots_info(
        self,
        canvas_size=(1000, 1000),
        overlap_ratio: float = 0.46,
        image_count: int = 2,
        uniform_scale: float = 1.46,
        center_compact_ratio: float = 0.80,
    ):
        if image_count != 2:
            raise ValueError("OverlapDoubleHorizontalUniformLayout requires 2 images")

        canvas_w, canvas_h = canvas_size
        base_w = canvas_w // 2

        slot_w = int(base_w * uniform_scale)
        overlap = int(base_w * overlap_ratio)
        raw_step = max(1, slot_w - overlap)
        # Slightly compress spacing so both subjects gather closer to center.
        step = max(1, int(raw_step * center_compact_ratio))

        center_x = canvas_w // 2
        half_w = slot_w // 2
        half_step = step // 2

        left_x = center_x - half_w - half_step
        right_x = center_x - half_w + half_step

        return [
            {"size": (slot_w, canvas_h), "pos": (left_x, 0)},
            {"size": (slot_w, canvas_h), "pos": (right_x, 0)},
        ]

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
        overlap_ratio: float = 0.46,
    ) -> Image.Image:
        if len(images) != 2:
            raise ValueError("OverlapDoubleHorizontalUniformLayout requires 2 images")

        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        slots = self.get_slots_info(canvas_size, overlap_ratio=overlap_ratio, image_count=2)

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            layer.paste(img_rgba, slot["pos"])
            canvas = Image.alpha_composite(canvas, layer)

        if to_rgb:
            from .utils import paste_on_prebuilt_bg

            return paste_on_prebuilt_bg(canvas)

        return canvas
