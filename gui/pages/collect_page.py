# gui/pages/collect_page.py

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from gui.widgets.center_popup import CenterPopup
from models.product_item import ProductItem


class CollectPage:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)

        self.pending_frame = None
        self.url_entry = None
        self.canvas = None
        self.canvas_window = None

    # ==========================================================
    # UI 구성
    # ==========================================================
    def build(self):
        top = ttk.Frame(self.frame)
        top.pack(fill="x", padx=10, pady=10)

        def show_supported_sites():
            popup = CenterPopup(
                parent=self.frame,
                title="소싱 사이트 목록",
                size=(300, 190),
            )

            # 파서 추가 시 여기에 사이트명을 추가하면 자동으로 번호가 붙습니다.
            sites = [
                "유니클로 / JP",
                "유니클로 / VN",
                "무인양품 / JP",
                "GU / JP",
                "SuperSports / JP",
            ]

            for idx, site in enumerate(sites, start=1):
                ttk.Label(popup, text=f"{idx}. {site}").pack(anchor="w", padx=14, pady=2)

            ttk.Button(popup, text="닫기", command=popup.destroy).pack(pady=10)

        ttk.Button(top, text="소싱 사이트 목록 ▼", command=show_supported_sites).pack(side="left", padx=(0, 8))

        self.url_entry = ttk.Entry(top)
        self.url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(top, text="추가하기", command=self.add_product).pack(side="left", padx=5)
        ttk.Button(top, text="정보수집하기", command=self.app.collect_all).pack(side="left", padx=5)

        # =========================
        # 스크롤 영역
        # =========================
        list_container = ttk.Frame(self.frame)
        list_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.pending_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.pending_frame, anchor="nw")

        self.pending_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width),
        )

        self._setup_mousewheel_binding()
        self.refresh()

    # ==========================================================
    # 마우스휠 바인딩
    # ==========================================================
    def _setup_mousewheel_binding(self):
        def bind_wheel(_e=None):
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows
            self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)  # Linux
            self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

        def unbind_wheel(_e=None):
            self.canvas.unbind_all("<MouseWheel>")
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")

        self.canvas.bind("<Enter>", bind_wheel)
        self.canvas.bind("<Leave>", unbind_wheel)
        self.pending_frame.bind("<Enter>", bind_wheel)
        self.pending_frame.bind("<Leave>", unbind_wheel)

    # ==========================================================
    # 스크롤 처리
    # ==========================================================
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    # ==========================================================
    def show(self):
        self.refresh()
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()

    # ==========================================================
    # 리스트 갱신
    # ==========================================================
    def refresh(self):
        for w in self.pending_frame.winfo_children():
            w.destroy()

        products = self.app.products_pending

        for idx, item in enumerate(products, start=1):
            row = ttk.Frame(self.pending_frame)
            row.pack(fill="x", pady=6)

            sep = tk.Frame(self.pending_frame, height=1, bg="#e0e0e0")
            sep.pack(fill="x", padx=5, pady=(0, 3))

            ttk.Label(
                row,
                text=f"{idx}.",
                width=4,
                anchor="e",
                foreground="#555",
                font=("맑은 고딕", 13, "bold"),
            ).pack(side="left", padx=(0, 5))

            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            ttk.Label(text_frame, text=item.url, font=("맑은 고딕", 10, "bold")).pack(anchor="w")

            status = getattr(item, "collect_status", "대기")
            color = "green" if status == "완료" else "gray"
            ttk.Label(text_frame, text=f"수집: {status}", foreground=color).pack(anchor="w")

            side = ttk.Frame(row)
            side.pack(side="right")

            ttk.Label(side, text=getattr(item, "added_at", ""), foreground="#666").pack(side="left", padx=(0, 10))
            ttk.Button(side, text="삭제", command=lambda p=item: self.delete_product(p)).pack(side="left")

    # ==========================================================
    def add_product(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("알림", "URL을 입력해 주세요.", parent=self.frame)
            return

        item = ProductItem(url)
        item.added_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.app.products_pending.append(item)
        self.url_entry.delete(0, tk.END)
        self.refresh()

    # ==========================================================
    def delete_product(self, item):
        if item in self.app.products_pending:
            self.app.products_pending.remove(item)
            self.refresh()
