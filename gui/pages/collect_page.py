# gui/pages/collect_page.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from models.product_item import ProductItem
from gui.widgets.center_popup import CenterPopup


class CollectPage:
    def __init__(self, parent, app):
        """
        parent : content 영역 frame
        app    : ProductCollectorGUI (상태/로직 공유)
        """
        self.app = app
        self.frame = ttk.Frame(parent)

        # 내부 프레임 참조
        self.pending_frame = None
        self.url_entry = None

    # ==========================================================
    # UI 구성
    # ==========================================================
    def build(self):

        # =========================
        # 상단 컨트롤 영역
        # =========================
        top = ttk.Frame(self.frame)
        top.pack(fill="x", padx=10, pady=10)

        # -------------------------
        # 소싱 사이트 목록 팝업
        # -------------------------
        def show_supported_sites():
            popup = CenterPopup(
                parent=self.frame,
                title="소싱 사이트 목록",
                size=(260, 150)
            )

            sites = [
                "유니클로 / JP",
                "유니클로 / VN",
                "무인양품 / JP",
                "GU / JP",
            ]

            for s in sites:
                ttk.Label(popup, text="• " + s).pack(anchor="w", padx=14, pady=2)

            ttk.Button(popup, text="닫기", command=popup.destroy).pack(pady=10)

        ttk.Button(
            top,
            text="소싱 사이트 목록 ▼",
            command=show_supported_sites
        ).pack(side="left", padx=(0, 8))

        # -------------------------
        # URL 입력창
        # -------------------------
        self.url_entry = ttk.Entry(top)
        self.url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(
            top,
            text="추가하기",
            command=self.add_product
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="정보수집하기",
            command=self.app.collect_all
        ).pack(side="left", padx=5)

        # =========================
        # 수집 대기 리스트 영역
        # =========================
        self.pending_frame = ttk.Frame(self.frame)
        self.pending_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh()

    # ==========================================================
    # 화면 표시 / 숨김
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

            # 구분선
            sep = tk.Frame(
                self.pending_frame,
                height=1,
                bg="#e0e0e0"
            )
            sep.pack(fill="x", padx=5, pady=(0, 3))

            # 번호
            ttk.Label(
                row,
                text=f"{idx}.",
                width=4,
                anchor="e",
                foreground="#555",
                font=("맑은 고딕", 13, "bold")
            ).pack(side="left", padx=(0, 5))

            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            # URL
            ttk.Label(
                text_frame,
                text=item.url,
                font=("맑은 고딕", 10, "bold")
            ).pack(anchor="w")

            status = getattr(item, "collect_status", "대기")
            color = "green" if status == "완료" else "gray"

            ttk.Label(
                text_frame,
                text=f"수집: {status}",
                foreground=color
            ).pack(anchor="w")

            side = ttk.Frame(row)
            side.pack(side="right")

            ttk.Label(
                side,
                text=getattr(item, "added_at", ""),
                foreground="#666"
            ).pack(side="left", padx=(0, 10))

            ttk.Button(
                side,
                text="삭제",
                command=lambda p=item: self.delete_product(p)
            ).pack(side="left")

    # ==========================================================
    # 상품 추가
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
    # 상품 삭제
    # ==========================================================
    def delete_product(self, item):

        if item in self.app.products_pending:
            self.app.products_pending.remove(item)
            self.refresh()
