# gui/product_detail/image_panel.py

import tkinter as tk
from tkinter import ttk
import logging

log = logging.getLogger(__name__)

from gui.widgets.scroll_frame import ScrollFrame
from gui.widgets.image_loader import load_image_async


class ImagePanel(ttk.LabelFrame):

    def __init__(self, parent, item, owner):
        super().__init__(parent, text="상품 이미지", padding=10)

        self.owner = owner
        self.item = item

        # 🔥 핵심 로그 1: parsed_raw 자체 확인
        log.debug(f"[UI][ImagePanel] parsed_raw keys={list(item.parsed_raw.keys())}")

        # 🔥 핵심 로그 2: images 원본 그대로 확인
        self.images = item.parsed_raw.get("images", [])
        log.debug(
            "[UI][ImagePanel] images loaded "
            f"type={type(self.images)} "
            f"count={len(self.images) if isinstance(self.images, list) else 'N/A'}"
        )

        if isinstance(self.images, list):
            for i, u in enumerate(self.images):
                log.debug(f"[UI][ImagePanel] images[{i}] = {repr(u)}")

        self.grid_propagate(False)
        self.pack_propagate(False)

        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True)
        self.inner = sf.inner

        self.refresh_images()

    # ---------------------------------------------------
    # 이미지 목록 표시
    # ---------------------------------------------------
    def refresh_images(self):
        for w in self.inner.winfo_children():
            w.destroy()

        log.debug(f"[UI][ImagePanel] refresh_images count={len(self.images)}")

        for idx, url in enumerate(self.images):
            log.debug(f"[UI][ImagePanel] render image[{idx}] url={repr(url)}")

            row = ttk.Frame(self.inner, padding=5)
            row.pack(fill="x", pady=5)

            lbl = ttk.Label(row, text="로딩중...")
            lbl.pack(side="left", padx=4)

            load_image_async(
                url,
                (140, 140),
                lambda img, lbl=lbl, u=url: (
                    log.debug(
                        f"[UI][ImagePanel] load_result url={repr(u)} success={bool(img)}"
                    ),
                    lbl.configure(image=img, text="") if img else lbl.configure(text="[오류]"),
                    setattr(lbl, "image", img)
                ),
                row
            )

            ttk.Button(row, text="X", width=3,
                       command=lambda i=idx: self.delete_img(i)).pack(side="right")

            ttk.Button(row, text="▲", width=2,
                       command=lambda i=idx: self.move_up(i)).pack(side="right")

            ttk.Button(row, text="▼", width=2,
                       command=lambda i=idx: self.move_down(i)).pack(side="right")

    # ---------------------------------------------------
    # 이미지 조작
    # ---------------------------------------------------
    def move_up(self, i):
        if i > 0:
            self.images[i], self.images[i - 1] = self.images[i - 1], self.images[i]
            self.item.thumbnail_url = self.images[0] if self.images else None
            self.refresh_images()

    def move_down(self, i):
        if i < len(self.images) - 1:
            self.images[i], self.images[i + 1] = self.images[i + 1], self.images[i]
            self.item.thumbnail_url = self.images[0] if self.images else None
            self.refresh_images()

    def delete_img(self, i):
        del self.images[i]
        self.item.thumbnail_url = self.images[0] if self.images else None
        self.refresh_images()

    # ---------------------------------------------------
    # save
    # ---------------------------------------------------
    def save(self):
        self.item.parsed_raw["images"] = self.images
        self.item.thumbnail_url = self.images[0] if self.images else None
