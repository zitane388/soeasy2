# gui/product_detail/description_panel.py

import tkinter as tk
from tkinter import ttk, messagebox
import os, json, tempfile, webbrowser, threading
import shutil

import tempfile
import subprocess

from utils.detail_description_generator import generate_detail_html
from utils.video_utils import download_and_convert_video
from utils.html_cleaner import text_to_html

from llm.llm_detail_generator import generate_sections_from_llm
from utils.html_cleaner import (
    html_to_text,
    text_to_html,
    format_description_blocks
)
from utils.detail_description_generator import (
    translate_header,
    normalize_size_chart,
    html_to_png_final
)

from gui.widgets.scroll_frame import ScrollFrame   # ★ ScrollFrame 적용 핵심

import logging
log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIZE_MAPPING_PATH = os.path.join(BASE_DIR, "..", "..", "templates", "size_header_mapping.json")
SIZE_MAPPING_PATH = os.path.abspath(SIZE_MAPPING_PATH)


class DescriptionPanel(ttk.LabelFrame):

    def __init__(self, parent, item, owner):
        super().__init__(parent, text="상세설명", padding=10)

        self.item = item
        self.owner = owner
        # ============================================================
        # ScrollFrame 사용
        # ============================================================
        sf = ScrollFrame(self)
        sf.grid(row=0, column=0, sticky="nsew")

        inner = sf.inner

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        inner.columnconfigure(0, weight=1)

        # ============================================================
        # ① 상세설명 TEXT
        # ============================================================
        detail_text = item.final_detail_text or item.detail_text or ""

        self.text_box = tk.Text(inner, wrap="word", height=27, font=("맑은 고딕", 10))
        self.text_box.grid(row=0, column=0, sticky="nsew",
                           padx=5, pady=(5, 10))
        self.text_box.insert("1.0", detail_text)

        # ============================================================
        # ② 상세설명 버튼
        # ============================================================
        btn_row = ttk.Frame(inner)
        btn_row.grid(row=1, column=0, pady=(5, 10), sticky="w")

        ttk.Button(btn_row, text="상세설명 생성",
                   command=self.generate_description).pack(side="left", padx=5)

        ttk.Button(btn_row, text="상세설명 저장",
                   command=self.save_description).pack(side="left", padx=5)

        # ★ 미리보기 버튼은 항상 표시
        ttk.Button(btn_row, text="미리보기",
                   command=self.preview_detail).pack(side="left", padx=5)

        # ============================================================
        # ③ 사이즈 헤더
        # ============================================================
        ttk.Label(inner, text="■ 사이즈 헤더").grid(
            row=2, column=0, sticky="w", pady=(20, 5)
        )

        original_headers = self.item.size_headers_original or []
        original_headers = list(dict.fromkeys(original_headers))

        # 매핑 로드
        def load_mapping():
            if not os.path.exists(SIZE_MAPPING_PATH):
                return {}
            try:
                with open(SIZE_MAPPING_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}

        current_mapping = load_mapping()

        # Entry UI
        map_frame = ttk.Frame(inner)
        map_frame.grid(row=3, column=0, sticky="ew", pady=10)

        style = ttk.Style()
        style.configure("Translated.TEntry", foreground="#777")
        style.configure("Mapped.TEntry", foreground="#000")

        self.left_entries = []
        self.right_entries = []

        for h in original_headers:
            rowf = ttk.Frame(map_frame)
            rowf.pack(fill="x", pady=2)

            rowf.columnconfigure(0, weight=1)
            rowf.columnconfigure(1, weight=1)

            e_left = ttk.Entry(rowf)
            e_left.insert(0, h)
            e_left.grid(row=0, column=0, padx=5, sticky="ew")
            self.left_entries.append(e_left)

            mapped = current_mapping.get(h)
            if mapped:
                display = mapped
                st = "Mapped.TEntry"
            else:
                display = translate_header(h)
                st = "Translated.TEntry"

            e_right = ttk.Entry(rowf, style=st)
            e_right.insert(0, display)
            e_right.grid(row=0, column=1, padx=5, sticky="ew")
            self.right_entries.append(e_right)

        ttk.Button(
            inner, text="헤더 매핑 파일 열기",
            command=self.open_header_json_editor
        ).grid(row=4, column=0, sticky="w", pady=(5, 20))

        # ============================================================
        # ④ 영상 정보
        # ============================================================
        ttk.Label(inner, text="■ 영상 파일").grid(
            row=5, column=0, sticky="w", pady=(10, 5)
        )

        video_frame = ttk.Frame(inner)
        video_frame.grid(row=6, column=0, sticky="ew", pady=(0, 10))

        if item.video_url:
            ttk.Label(video_frame, text=f"영상 있음: {item.video_url}", foreground="#333")\
                .pack(anchor="w")
        else:
            ttk.Label(video_frame, text="영상 없음", foreground="#999")\
                .pack(anchor="w")


    # ============================================================
    # 상세설명 생성
    # ============================================================
    

    def generate_description(self):
        original_text = self.item.detail_text or ""
        log.info("[UI] generate_description called | detail_len=%d", len(original_text))

        if not original_text.strip():
            log.warning("[UI] empty detail_text -> abort")
            messagebox.showwarning(
                "알림", "원본 상세설명이 없습니다.",
                parent=self.winfo_toplevel()
            )
            return

        top = self.winfo_toplevel()
        top.attributes("-topmost", True)

        def worker():
            log.info("[UI] worker start")
            try:
                llm_html = generate_sections_from_llm(original_text)
                log.info("[UI] llm_html received | len=%d", len(llm_html or ""))

                text_raw = html_to_text(llm_html)
                log.info("[UI] html_to_text done | len=%d", len(text_raw or ""))

                final_text = format_description_blocks(text_raw)
                log.info("[UI] format_description_blocks done | len=%d", len(final_text or ""))

                def apply_ui():
                    log.info("[UI] apply_ui start")
                    self.text_box.delete("1.0", "end")
                    self.text_box.insert("1.0", final_text)

                    self.item.final_detail_text = final_text
                    self.item.final_detail_html = llm_html

                    top.lift()
                    top.focus_force()
                    top.after(50, lambda: top.attributes("-topmost", False))
                    log.info("[UI] apply_ui end")

                top.after(0, apply_ui)

            except Exception as e:
                log.exception("[UI] worker error: %s", e)
                top.after(
                    0,
                    lambda: messagebox.showerror(
                        "오류", f"상세설명 생성 중 오류:\n{e}",
                        parent=top
                    )
                )

            finally:
                log.info("[UI] worker end")

        threading.Thread(target=worker, daemon=True).start()



    # ============================================================
    # 상세설명 저장
    # ============================================================
    def save_description(self):
        new_text = self.text_box.get("1.0", "end").strip()
        self.item.final_detail_text = new_text
        self.item.final_detail_html = text_to_html(new_text)

    # ============================================================
    # 상세설명 미리보기 (HTML 생성 후 브라우저 열기)
    # ============================================================
    def preview_detail(self):
        """
        상세설명 미리보기(Chrome) — 영상·HTML·사이즈표까지 포함한 정식 버전
        """

        # --------------------------------------------------------------
        # 1) 현재 텍스트 자동 저장
        # --------------------------------------------------------------
        new_text = self.text_box.get("1.0", "end").strip()
        self.item.final_detail_text = new_text
        self.item.final_detail_html = text_to_html(new_text)

        # --------------------------------------------------------------
        # 2) 영상 다운로드 + 변환 (mp4)
        # --------------------------------------------------------------
        if self.item.video_url:
            mp4_path = download_and_convert_video(self.item.video_url)
            if mp4_path:
                mp4_path = os.path.abspath(mp4_path)
            self.item.video_file = mp4_path
        else:
            self.item.video_file = None

        # --------------------------------------------------------------
        # 3) 상세 HTML 생성
        # --------------------------------------------------------------
        html = generate_detail_html(self.item)

        # --------------------------------------------------------------
        # 4) 임시 경로에 HTML 파일 저장
        # --------------------------------------------------------------
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "detail_preview.html")
        temp_path = os.path.abspath(temp_path)

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html)

        # --------------------------------------------------------------
        # 5) Chrome 실행 파일 경로 탐색
        # --------------------------------------------------------------
        default_chrome = shutil.which("chrome") or "chrome"

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            rf"C:\Users\{os.getlogin()}\AppData\Local\Google\Chrome\Application\chrome.exe",
            default_chrome
        ]

        chrome_path = next((p for p in chrome_paths if os.path.exists(p)), default_chrome)

        # --------------------------------------------------------------
        # 6) file:/// URL 구성
        # --------------------------------------------------------------
        file_url = "file:///" + temp_path.replace("\\", "/")

        # --------------------------------------------------------------
        # 7) Chrome app 모드로 팝업 실행
        # --------------------------------------------------------------
        try:
            subprocess.Popen([
                chrome_path,
                f"--app={file_url}",
                "--window-size=900,1600",
                "--disable-infobars",
                "--disable-extensions",
                "--force-device-scale-factor=1",
            ])
        except Exception as e:
            messagebox.showerror("오류", f"Chrome 미리보기 실행 실패\n\n{e}")


    # ============================================================
    # size_header_mapping.json 편집기
    # ============================================================
    def open_header_json_editor(self):
        top = tk.Toplevel(self)
        top.title("size_header_mapping.json 편집")
        top.geometry("700x650")

        txt = tk.Text(top, wrap="none")
        txt.pack(expand=True, fill="both")

        if os.path.exists(SIZE_MAPPING_PATH):
            with open(SIZE_MAPPING_PATH, "r", encoding="utf-8") as f:
                txt.insert("1.0", f.read())
        else:
            txt.insert("1.0", "{}")

        def save_json():
            try:
                raw = txt.get("1.0", "end")
                json.loads(raw)

                with open(SIZE_MAPPING_PATH, "w", encoding="utf-8") as f:
                    f.write(raw)

                new_mapping = json.loads(raw)

                # UI 업데이트
                for left, right in zip(self.left_entries, self.right_entries):
                    key = left.get().strip()
                    val = new_mapping.get(key, "")
                    right.delete(0, "end")
                    right.insert(0, val)

                # 사이즈 HTML 재생성
                self.item.size_html = normalize_size_chart(
                    self.item.size_headers_original,
                    self.item.size_rows_original
                )

                messagebox.showinfo("저장됨", "size_header_mapping.json 저장 완료", parent=top)
                top.destroy()

            except Exception as e:
                messagebox.showerror("오류", f"JSON 형식 오류:\n{e}", parent=top)

        ttk.Button(top, text="저장", command=save_json).pack(pady=5)

    # ============================================================
    # detail_window → save_all() 연동용
    # ============================================================
    def save(self):
        self.save_description()
