# image_tools/thumbnail_engine/box/base.py

from dataclasses import dataclass
from ..logger import get_logger

log = get_logger()


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self):
        return self.x

    @property
    def top(self):
        return self.y

    @property
    def right(self):
        return self.x + self.w

    @property
    def bottom(self):
        return self.y + self.h

    @property
    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    @property
    def top_center(self):
        return (self.x + self.w / 2, self.y)

    def apply_padding(self, padding: dict):
        log.debug(
            "apply_padding start "
            "before=(%.1f,%.1f,%.1f,%.1f) "
            "padding={top:%.3f,bottom:%.3f,left:%.3f,right:%.3f}",
            self.x, self.y, self.w, self.h,
            padding["top"], padding["bottom"],
            padding["left"], padding["right"],
        )

        pad_top = self.h * padding["top"]
        pad_bottom = self.h * padding["bottom"]
        pad_left = self.w * padding["left"]
        pad_right = self.w * padding["right"]

        new_box = Box(
            x=self.x - pad_left,
            y=self.y - pad_top,
            w=self.w + pad_left + pad_right,
            h=self.h + pad_top + pad_bottom,
        )

        log.debug(
            "apply_padding done "
            "after=(%.1f,%.1f,%.1f,%.1f)",
            new_box.x, new_box.y, new_box.w, new_box.h,
        )

        return new_box

    # --------------------------
    # clamp to image bounds
    # --------------------------
    def clamp(self, img_w: int, img_h: int):
        log.debug(
            "clamp start "
            "box=(%.1f,%.1f,%.1f,%.1f) image_size=(%d,%d)",
            self.x, self.y, self.w, self.h,
            img_w, img_h,
        )

        x1 = max(0, self.left)
        y1 = max(0, self.top)
        x2 = min(img_w, self.right)
        y2 = min(img_h, self.bottom)

        w = max(1, x2 - x1)
        h = max(1, y2 - y1)

        new_box = Box(x=x1, y=y1, w=w, h=h)

        if (
            self.x != new_box.x
            or self.y != new_box.y
            or self.w != new_box.w
            or self.h != new_box.h
        ):
            log.warning(
                "clamp applied "
                "from=(%.1f,%.1f,%.1f,%.1f) "
                "to=(%.1f,%.1f,%.1f,%.1f)",
                self.x, self.y, self.w, self.h,
                new_box.x, new_box.y, new_box.w, new_box.h,
            )
        else:
            log.debug("clamp skipped (box already inside image)")

        return new_box
