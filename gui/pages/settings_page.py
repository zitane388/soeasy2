# gui/pages/settings_page.py

import tkinter as tk
from tkinter import ttk


class SettingsPage:
    def __init__(self, parent, app):
        """
        parent : content 영역 frame
        app    : ProductCollectorGUI (전역 상태 접근 가능)
        """
        self.app = app
        self.frame = ttk.Frame(parent)

        # 설정 변수들 (추후 config 연동)
        self.var_naver_id = tk.StringVar()
        self.var_naver_pw = tk.StringVar()
        self.var_headless = tk.BooleanVar(value=False)

        self.var_windly_id = tk.StringVar()
        self.var_windly_pw = tk.StringVar()

    # ==========================================================
    # UI 구성
    # ==========================================================
    def build(self):

        # ===============================
        # 네이버 설정
        # ===============================
        self._build_section(
            title="네이버 설정",
            rows=[
                ("아이디", self.var_naver_id),
                ("비밀번호", self.var_naver_pw, True),
                ("헤드리스 모드", self.var_headless),
            ]
        )

        # ===============================
        # 윈들리 설정
        # ===============================
        self._build_section(
            title="윈들리 설정",
            rows=[
                ("아이디", self.var_windly_id),
                ("비밀번호", self.var_windly_pw, True),
            ]
        )

        # ===============================
        # 기타 설정
        # ===============================
        self._build_section(
            title="기타",
            rows=[
                ("자동 수집 옵션", None),
                ("디버그 모드", None),
            ]
        )

        # ===============================
        # 저장 버튼 (아직 동작 없음)
        # ===============================
        ttk.Button(
            self.frame,
            text="설정 저장",
            command=self.save_settings
        ).pack(anchor="e", padx=20, pady=20)

    # ==========================================================
    # 섹션 생성 유틸
    # ==========================================================
    def _build_section(self, title, rows):

        box = ttk.LabelFrame(self.frame, text=title)
        box.pack(fill="x", padx=20, pady=10)

        for row in rows:
            label = row[0]
            var = row[1]
            is_password = len(row) > 2 and row[2]

            line = ttk.Frame(box)
            line.pack(fill="x", pady=5, padx=10)

            ttk.Label(
                line,
                text=label,
                width=12
            ).pack(side="left")

            if isinstance(var, tk.BooleanVar):
                ttk.Checkbutton(
                    line,
                    variable=var
                ).pack(side="left")
            elif isinstance(var, tk.StringVar):
                ttk.Entry(
                    line,
                    textvariable=var,
                    show="*" if is_password else ""
                ).pack(side="left", fill="x", expand=True)
            else:
                ttk.Label(
                    line,
                    text="(추후 구현)"
                ).pack(side="left")

    # ==========================================================
    # 화면 표시 / 숨김
    # ==========================================================
    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()

    # ==========================================================
    # 저장 (구조만)
    # ==========================================================
    def save_settings(self):
        """
        TODO:
        - config 파일 로드/저장
        - 유효성 검사
        - 보안 처리
        """
        print("[SETTINGS] save_settings called (not implemented)")
