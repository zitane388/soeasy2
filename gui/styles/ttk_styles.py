# gui/styles/ttk_styles.py
import tkinter as tk
from tkinter import ttk

def setup_ttk_styles(root):
    style = ttk.Style(root)

    # -------------------------------
    # 전역 테마
    # -------------------------------
    # style.theme_use("default")

    # -------------------------------
    # LabelFrame 제목 스타일
    # -------------------------------
    style.configure(
        "TLabelframe",
        borderwidth=1,
        relief="solid"
    )
    style.configure(
        "TLabelframe.Label",
        font=("맑은 고딕", 10, "bold"),
        foreground="#333",
        padding=4
    )

    # -------------------------------
    # Notebook (탭)
    # -------------------------------
    style.configure(
        "TNotebook.Tab",
        padding=(10, 5),
        font=("맑은 고딕", 10)
    )

    style.map(
        "TNotebook.Tab",
        background=[("selected", "#ffffff")],
        foreground=[("selected", "#000")],
    )

    # -------------------------------
    # Button
    # -------------------------------
    style.configure(
        "TButton",
        padding=3,
        font=("맑은 고딕", 9)
    )

    # -------------------------------
    # Scrollbar
    # -------------------------------
    style.configure(
        "Vertical.TScrollbar",
        gripcount=0,
        background="#ddd",
        troughcolor="#f2f2f2",
        bordercolor="#ccc",
        arrowcolor="#555"
    )

    # -------------------------------
    # Entry, Text 주변 색
    # -------------------------------
    style.configure("TEntry", padding=4)
