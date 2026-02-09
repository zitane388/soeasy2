# gui/widgets/scroll_frame.py

import tkinter as tk
from tkinter import ttk


class ScrollFrame(ttk.Frame):
    """
    스크롤 가능한 프레임.
    어떤 패널이든 이 ScrollFrame을 사용하면 내부에 많은 위젯을
    세로로 쌓을 수 있고 자동으로 스크롤이 가능해진다.

    사용법:
        sf = ScrollFrame(parent)
        inner = sf.inner      # 내부에 위젯 추가
        sf.pack(fill="both", expand=True)
    """

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # 캔버스 + 스크롤바
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scroll_y = ttk.Scrollbar(self, orient="vertical",
                                      command=self.canvas.yview)

        # 내부 프레임
        self.inner = ttk.Frame(self.canvas)
        self.inner_id = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw"
        )

        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        # 배치
        self.canvas.pack(fill="both", expand=True, side="left")
        self.scroll_y.pack(fill="y", side="right")

        # 내부 프레임 크기에 따라 스크롤 영역 자동 적용
        self.inner.bind("<Configure>", self._on_frame_configure)

        # 캔버스가 리사이즈될 때 내부 프레임의 폭을 동일하게 유지
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 마우스 휠 스크롤
        self._bind_mousewheel()

    # ------------------------------------------------------------
    # 스크롤 영역 갱신
    # ------------------------------------------------------------
    def _on_frame_configure(self, event):
        bbox = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=bbox)

    # ------------------------------------------------------------
    # 내부 프레임 폭을 캔버스 폭에 맞춤
    # ------------------------------------------------------------
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.inner_id, width=event.width)

    # ------------------------------------------------------------
    # 마우스 휠 바인딩 (독립 동작, 기존 gui.py 코드와 충돌 없음)
    # ------------------------------------------------------------
    def _bind_mousewheel(self):
        def _wheel(event):
            # Windows
            delta = int(-1 * (event.delta / 120))
            self.canvas.yview_scroll(delta, "units")

        self.inner.bind("<Enter>", lambda e: self.inner.bind_all("<MouseWheel>", _wheel))
        self.inner.bind("<Leave>", lambda e: self.inner.unbind_all("<MouseWheel>")
                        )
