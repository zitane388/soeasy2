# gui/widgets/center_popup.py
import tkinter as tk


class CenterPopup(tk.Toplevel):
    def __init__(self, parent, title=None, size=None, modal=True):
        super().__init__(parent)

        self.parent = parent

        if title:
            self.title(title)

        self.resizable(False, False)
        self.transient(parent)

        if modal:
            self.grab_set()

        # geometry 지정 전에 반드시 표시 준비
        self.update_idletasks()
        self.wait_visibility()

        # 크기 결정
        if size:
            w, h = size
        else:
            w = self.winfo_width()
            h = self.winfo_height()

        # 부모 기준 중앙 좌표 계산
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2

        self.geometry(f"{w}x{h}+{x}+{y}")
