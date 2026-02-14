from PIL import Image


class OverlapQuadHorizontalUniformLayout:
    """
    Upper-body 4-person overlap layout.
    Uses uniform slot widths and symmetric overlap around canvas center.
    """

    def get_slots_info(
        self,
        canvas_size=(1000, 1000),
        overlap_ratio: float = 0.64,
        image_count: int = 4,
        uniform_scale: float = 2.36,
        center_compact_ratio: float = 0.52,
        outer_inward_ratio: float = 0.30,
    ):
        if image_count != 4:
            raise ValueError("OverlapQuadHorizontalUniformLayout requires 4 images")

        canvas_w, canvas_h = canvas_size
        base_w = canvas_w // 4

        slot_w = int(base_w * uniform_scale)
        overlap = int(base_w * overlap_ratio)
        raw_step = max(1, slot_w - overlap)
        # Tighten spacing so subjects gather toward center and overlap more.
        step = max(1, int(raw_step * center_compact_ratio))

        center_x = canvas_w // 2
        half_w = slot_w // 2

        left_outer_x = center_x - half_w - int(1.5 * step)
        left_inner_x = center_x - half_w - int(0.5 * step)
        right_inner_x = center_x - half_w + int(0.5 * step)
        right_outer_x = center_x - half_w + int(1.5 * step)

        # Pull only the outer pair inward without moving inner pair.
        outer_pull = int(base_w * outer_inward_ratio)
        left_outer_x += outer_pull
        right_outer_x -= outer_pull

        return [
            {"size": (slot_w, canvas_h), "pos": (left_outer_x, 0)},
            {"size": (slot_w, canvas_h), "pos": (right_outer_x, 0)},
            {"size": (slot_w, canvas_h), "pos": (left_inner_x, 0)},
            {"size": (slot_w, canvas_h), "pos": (right_inner_x, 0)},
        ]

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
        overlap_ratio: float = 0.64,
        outer_inward_ratio: float = 0.30,
    ) -> Image.Image:
        if len(images) != 4:
            raise ValueError("OverlapQuadHorizontalUniformLayout requires 4 images")

        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        slots = self.get_slots_info(
            canvas_size,
            overlap_ratio=overlap_ratio,
            image_count=4,
            outer_inward_ratio=outer_inward_ratio,
        )

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            layer.paste(img_rgba, slot["pos"])
            canvas = Image.alpha_composite(canvas, layer)

        if to_rgb:
            from .utils import paste_on_prebuilt_bg

            return paste_on_prebuilt_bg(canvas)

        return canvas
