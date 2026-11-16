# image_tools/thumbnail_engine/layout/base_layout.py

class BaseLayout:
    def apply(self, images, canvas_size, **kwargs):
        raise NotImplementedError
