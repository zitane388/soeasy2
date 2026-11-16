# gui/pages/extra_page.py

import threading
from tkinter import ttk, messagebox


class ExtraPage:
    def __init__(self, parent, app):
        """
        parent : content 영역 frame
        app    : ProductCollectorGUI (전역 상태 접근)
        """
        self.app = app
        self.frame = ttk.Frame(parent)

        self.status_label = None

    # ==========================================================
    # UI 구성
    # ==========================================================
    def build(self):
        
        # ===============================
        # 윈들리 관련 기능
        # ===============================
        windly_box = ttk.LabelFrame(self.frame, text="윈들리 관리")
        windly_box.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            windly_box,
            text="윈들리 카테고리 정보를 수집·갱신합니다.\n"
                 "카테고리 자동 매칭 및 템플릿 기능에 사용됩니다.",
            foreground="#555",
            justify="left"
        ).pack(anchor="w", padx=10, pady=(5, 10))

        ttk.Button(
            windly_box,
            text="윈들리 카테고리 수집 실행",
            command=self.run_windly_category_collect
        ).pack(anchor="w", padx=10, pady=(0, 5))

        self.status_label = ttk.Label(
            windly_box,
            text="대기중",
            foreground="gray"
        )
        self.status_label.pack(anchor="w", padx=10, pady=(5, 10))

        # ===============================
        # 기타 유틸 (확장 예정)
        # ===============================
        util_box = ttk.LabelFrame(self.frame, text="기타 유틸리티")
        util_box.pack(fill="x", padx=20, pady=10)

        ttk.Label(
            util_box,
            text="추후 내부 관리·테스트 기능이 이 영역에 추가됩니다.",
            foreground="#888"
        ).pack(anchor="w", padx=10, pady=10)

    # ==========================================================
    # 화면 표시 / 숨김
    # ==========================================================
    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()

    # ==========================================================
    # 윈들리 카테고리 수집
    # ==========================================================
    def run_windly_category_collect(self):
        """
        기존 main_window.run_windly_category_collect()
        기능을 그대로 이전
        """

        from automation.windly.windly_category_collector import (
            main as windly_category_collect_main
        )

        def task():
            try:
                self.frame.after(0, lambda: (
                    self.status_label.config(
                        text="윈들리 카테고리 수집 중...",
                        foreground="blue"
                    ),
                    self.app.upload_status_label_global.config(
                        text="윈들리 카테고리 수집 중..."
                    )
                ))

                windly_category_collect_main()

                self.frame.after(0, lambda: (
                    self.status_label.config(
                        text="윈들리 카테고리 수집 완료",
                        foreground="green"
                    ),
                    self.app.upload_status_label_global.config(
                        text="윈들리 카테고리 수집 완료"
                    ),
                    messagebox.showinfo(
                        "완료",
                        "윈들리 카테고리 수집이 완료되었습니다."
                    )
                ))

            except Exception as e:
                self.frame.after(0, lambda: (
                    self.status_label.config(
                        text="윈들리 카테고리 수집 실패",
                        foreground="red"
                    ),
                    self.app.upload_status_label_global.config(
                        text="윈들리 카테고리 수집 실패"
                    ),
                    messagebox.showerror(
                        "오류",
                        f"윈들리 카테고리 수집 중 오류 발생\n\n{e}"
                    )
                ))

        threading.Thread(target=task, daemon=True).start()
