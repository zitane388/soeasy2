from PIL import Image


class OverlapTripleHorizontalUniformLayout:
    """
    Upper-body 3-person overlap layout.
    Left/center/right all use widened slot widths and overlap symmetrically.
    """

    def get_slots_info(
        self,
        canvas_size=(1000, 1000),
        overlap_ratio: float = 0.32,
        image_count: int = 3,
        uniform_scale: float = 1.58,
        edge_inset_ratio: float = 0.36,
        center_extra_ratio: float = 0.14,
    ):
        if image_count != 3:
            raise ValueError("OverlapTripleHorizontalUniformLayout requires 3 images")

        canvas_w, canvas_h = canvas_size
        base_w = canvas_w // 3
        slot_w = int(base_w * uniform_scale)
        center_w = int(slot_w * (1.0 + center_extra_ratio))
        overlap = int(base_w * overlap_ratio)
        edge_inset = int(base_w * edge_inset_ratio)

        # Geometry-only tuning:
        # 1) center slot gets extra width for more side padding feeling
        # 2) left/right are moved slightly inward to avoid edge clipping
        center_mid_x = canvas_w // 2
        center_x = center_mid_x - (center_w // 2)
        # Symmetric placement around canvas center.
        # Keep clipping-allowed behavior, but avoid one-sided over-clipping.
        left_x = center_mid_x - (slot_w // 2) - (slot_w - overlap) + edge_inset
        right_x = center_mid_x - (slot_w // 2) + (slot_w - overlap) - edge_inset

        return [
            {"size": (slot_w, canvas_h), "pos": (left_x, 0)},
            {"size": (slot_w, canvas_h), "pos": (right_x, 0)},
            {"size": (center_w, canvas_h), "pos": (center_x, 0)},
        ]

    def apply(
        self,
        images: list[Image.Image],
        canvas_size=(1000, 1000),
        to_rgb: bool = False,
        overlap_ratio: float = 0.32,
    ) -> Image.Image:
        if len(images) != 3:
            raise ValueError("OverlapTripleHorizontalUniformLayout requires 3 images")

        canvas_w, canvas_h = canvas_size
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        slots = self.get_slots_info(canvas_size, overlap_ratio=overlap_ratio, image_count=3)

        for img, slot in zip(images, slots):
            img_rgba = img.convert("RGBA")
            layer = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            layer.paste(img_rgba, slot["pos"])
            canvas = Image.alpha_composite(canvas, layer)

        if to_rgb:
            from .utils import paste_on_prebuilt_bg

            return paste_on_prebuilt_bg(canvas)

        return canvas
