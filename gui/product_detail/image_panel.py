# gui/product_detail/image_panel.py

import tkinter as tk
from tkinter import ttk
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

from gui.widgets.scroll_frame import ScrollFrame
from gui.widgets.image_loader import load_image_async
from image_tools.image_source_resolver import resolve_item_image_sources


class ImagePanel(ttk.LabelFrame):

    def __init__(self, parent, item, owner):
        super().__init__(parent, text="상품 이미지", padding=10)

        self.owner = owner
        self.item = item

        if not hasattr(self.item, "image_checked_map"):
            self.item.image_checked_map = {}

        # 🔥 핵심 로그 2: images 원본 그대로 확인
        self.images = resolve_item_image_sources(item)
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

        for idx, src in enumerate(self.images):
            row = ttk.Frame(self.inner, padding=5)
            row.pack(fill="x", pady=6)

            # ===============================
            # 1️⃣ 체크 상태 (item 기준)
            # ===============================
            checked = tk.BooleanVar(
                value=self.item.image_checked_map.get(src, False)
            )

            def on_toggle(v=checked, s=src):
                self.item.image_checked_map[s] = v.get()

            chk = ttk.Checkbutton(
                row,
                variable=checked,
                command=on_toggle,
                takefocus=False
            )
            chk.pack(side="left", padx=(4, 8))

            # ===============================
            # 2️⃣ 이미지
            # ===============================
            lbl = ttk.Label(row, text="로딩중...")
            lbl.pack(side="left", padx=4)

            def toggle_from_image(event, v=checked, s=src):
                v.set(not v.get())
                self.item.image_checked_map[s] = v.get()

            lbl.bind("<Button-1>", toggle_from_image)

            load_image_async(
                src,
                (140, 140),
                lambda img, lbl=lbl: (
                    lbl.configure(image=img, text=""),
                    setattr(lbl, "image", img)
                ) if img else lbl.configure(text="[오류]"),
                row
            )

            # ===============================
            # 3️⃣ 버튼 컬럼 (세로)
            # ===============================
            btn_col = ttk.Frame(row)
            btn_col.pack(side="right", padx=6)

            ttk.Button(
                btn_col, text="▲", width=2,
                command=lambda i=idx: self.move_up(i)
            ).pack(fill="x", pady=1)

            ttk.Button(
                btn_col, text="▼", width=2,
                command=lambda i=idx: self.move_down(i)
            ).pack(fill="x", pady=1)

            ttk.Button(
                btn_col, text="X", width=2,
                command=lambda i=idx: self.delete_img(i)
            ).pack(fill="x", pady=1)

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
        self.item.final_image_sources = self.images
        self.item.thumbnail_url = self.images[0] if self.images else None
