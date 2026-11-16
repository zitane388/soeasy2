# gui/product_detail/formatter_panel.py
import tkinter as tk
from tkinter import ttk, messagebox
import os
import importlib

class FormatterPanel:
    FORMATTER_PATH = None   # detail_window 에서 주입

    @staticmethod
    def open_formatter_editor(parent_window):
        path = FormatterPanel.FORMATTER_PATH
        print(f"[DEBUG] Opening Formatter Editor. Path: {path}")

        if not path or not os.path.exists(path):
            messagebox.showerror(
                "오류",
                f"Formatter 파일을 찾을 수 없습니다:\n{path}",
                parent=parent_window
            )
            return

        editor = tk.Toplevel(parent_window)
        editor.title("LLM Formatter 편집기")
        editor.geometry("900x700")
        editor.attributes("-topmost", True)

        frame = ttk.Frame(editor)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(frame)
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = ttk.Scrollbar(frame, orient="horizontal")
        scrollbar_x.pack(side="bottom", fill="x")

        text = tk.Text(
            frame, wrap="none", undo=True,
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        text.pack(fill="both", expand=True)

        scrollbar_y.config(command=text.yview)
        scrollbar_x.config(command=text.xview)

        with open(path, "r", encoding="utf-8") as f:
            text.insert("1.0", f.read())

        def save_changes():
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text.get("1.0", "end-1c"))

                import llm.llm_client as llm_client
                import llm.llm_formatter as llm_formatter
                importlib.reload(llm_formatter)

                if hasattr(llm_client, "reload_formatter"):
                    llm_client.reload_formatter()

                messagebox.showinfo("저장 완료", "즉시 반영되었습니다.", parent=editor)
                editor.destroy()
            except Exception as e:
                messagebox.showerror("저장 오류", str(e), parent=editor)

        btn = ttk.Frame(editor)
        btn.pack(fill="x", pady=5)
        ttk.Button(btn, text="저장 후 반영", command=save_changes).pack(side="right", padx=10)
        ttk.Button(btn, text="취소", command=editor.destroy).pack(side="right")
