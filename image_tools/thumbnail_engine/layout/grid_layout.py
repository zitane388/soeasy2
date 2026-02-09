# image_tools/thumbnail_engine/layout/grid_layout.py

from PIL import Image
import math


class GridLayout:
    def apply(
        self,
        images: list,
        canvas_size: tuple,
        cols: int,
        background_color=(255, 255, 255),
    ) -> Image.Image:
        """
        images : [Image, ...]
        cols   : 열 개수
        """

        canvas_w, canvas_h = canvas_size
        rows = math.ceil(len(images) / cols)

        cell_w = canvas_w // cols
        cell_h = canvas_h // rows

        canvas = Image.new("RGB", canvas_size, background_color)

        for idx, img in enumerate(images):
            col = idx % cols
            row = idx // cols

            resized = img.resize((cell_w, cell_h), Image.LANCZOS)
            canvas.paste(
                resized,
                (col * cell_w, row * cell_h),
            )

        return canvas
