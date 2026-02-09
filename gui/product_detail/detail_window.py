# gui/product_detail/detail_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import webbrowser


from .thumb_panel import ThumbnailPanel
from .image_panel import ImagePanel
from .name_panel import NamePanel
from .option_panel import OptionPanel
from .description_panel import DescriptionPanel
from .formatter_panel import FormatterPanel
from .utils import Toast
from gui.widgets.center_popup import CenterPopup


# ------------------------------------------------------------
# 절대경로 기반 Formatter 경로
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
from utils.path import p  # 이미 만들어둔 경로 유틸리티 임포트

# ------------------------------------------------------------
# 수정된 부분: 이제 p() 함수가 _MEIPASS를 기준으로 경로를 찾아줍니다.
# ------------------------------------------------------------
FormatterPanel.FORMATTER_PATH = p("llm", "llm_formatter.py")


class DetailWindow(CenterPopup):
    """
    패널들이 공통으로 사용하는 중앙 컨트롤러 역할.
    messagebox도 여기서만 호출하도록 통일.
    """

    def __init__(self, parent, item, refresh_callback=None):
        super().__init__(
            parent=parent,
            title="상품 상세정보",
            size=(1700, 950),
            modal=False
        )

        self.parent = parent
        self.item = item
        self.app = parent.app
        self.refresh_callback = refresh_callback
        
        # -------------------------
        # 창 구성
        # -------------------------
        self.configure(bg="#f7f7f7")
        self.rowconfigure(0, weight=1)  # 본문
        self.rowconfigure(1, weight=0)  # 하단 버튼
        self.columnconfigure(0, weight=1)

        # --------------------------------------------------
        # 본문
        # --------------------------------------------------
        content = ttk.Frame(self)
        content.grid(row=0, column=0, sticky="nsew")


        content.columnconfigure(0, weight=4, uniform="col")
        content.columnconfigure(1, weight=3, uniform="col")
        content.columnconfigure(2, weight=4, uniform="col")
        content.columnconfigure(3, weight=3, uniform="col")
        content.columnconfigure(4, weight=4, uniform="col")
        content.rowconfigure(0, weight=1)

        # ======================================================
        # 패널 생성
        # ======================================================
        self.thumb_panel = ThumbnailPanel(content, item, owner=self)
        self.thumb_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.image_panel = ImagePanel(content, item, owner=self)
        self.image_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.name_panel = NamePanel(content, item, owner=self)
        self.name_panel.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        self.option_panel = OptionPanel(content, item, owner=self)
        self.option_panel.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)

        self.desc_panel = DescriptionPanel(content, item, owner=self)
        self.desc_panel.grid(row=0, column=4, sticky="nsew", padx=5, pady=5)

        # -------------------------
        # 하단 버튼
        # -------------------------
        bottom = ttk.Frame(self)
        bottom.grid(row=1, column=0, sticky="ew", pady=10)

        ttk.Button(bottom, text="저장/닫기", command=self.save_all).pack(side="right", padx=10)
        
        ttk.Button(
            bottom,
            text="프롬프트",
            command=lambda: FormatterPanel.open_formatter_editor(self)
        ).pack(side="right", padx=6)
        
        ttk.Button(
            bottom,
            text="원본 상품",
            command=self.open_original_product
        ).pack(side="right", padx=6)
        
    def open_original_product(self):
        url = (
            getattr(self.item, "url", None)
            or self.item.parsed_raw.get("url")
            or self.item.parsed_raw.get("original_url")
        )

        if not url:
            self.show_warning("원본 상품 URL이 없습니다.")
            return

        webbrowser.open(url)


    # ======================================================
    # 메시지박스 통합 처리 메서드
    # ======================================================
    def show_warning(self, msg):
        messagebox.showwarning("경고", msg)

    def show_error(self, msg):
        messagebox.showerror("오류", msg)

    def show_info(self, msg):
        messagebox.showinfo("안내", msg)

    # ======================================================
    # 저장 기능
    # ======================================================
    def save_all(self):
        self.name_panel.save()
        self.desc_panel.save()
        self.option_panel.save()
        self.image_panel.save()
        self.thumb_panel.save()

        Toast.show(self, "저장되었습니다.")
        if self.refresh_callback:
            self.refresh_callback()
        self.destroy()
        
    def get_app(self):
        w = self
        while w:
            if hasattr(w, "app"):
                return w.app
            w = getattr(w, "parent", None)
        raise RuntimeError("app not found")


def open_detail_window(root, item, refresh_callback=None):
    return DetailWindow(
        root,
        item,
        refresh_callback,
    )
