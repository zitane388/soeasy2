# gui/pages/collected_page.py

import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from gui.product_detail.detail_window import open_detail_window
from gui.widgets.image_loader import load_image_async, load_local_image_async


class CollectedPage:
    def __init__(self, parent, app):
        """
        parent : content 영역 frame
        app    : ProductCollectorGUI (상태/로직 공유)
        """
        self.app = app
        self.frame = ttk.Frame(parent)

        self.list_container = None
        self.select_all_var = tk.BooleanVar(value=True)

    # ==========================================================
    # UI 구성
    # ==========================================================
    def build(self):

        # ===============================
        # 상단 버튼 영역
        # ===============================
        header = ttk.Frame(self.frame)
        header.pack(fill="x", pady=5, padx=10)

        # 전체 선택 체크박스
        def toggle_select_all():
            val = self.select_all_var.get()
            for item in self.app.products_collected:
                item.checked = val
            self.refresh()

        ttk.Checkbutton(
            header,
            text="전체 선택",
            variable=self.select_all_var,
            command=toggle_select_all
        ).pack(side="left", padx=10)

        ttk.Button(
            header,
            text="썸네일 생성",
            command=lambda: threading.Thread(
                target=self.generate_all_thumbnails,
                daemon=True
            ).start()
        ).pack(side="left", padx=10)

        ttk.Button(
            header,
            text="네이버 상품등록",
            command=lambda: threading.Thread(
                target=self.upload_to_naver,
                daemon=True
            ).start()
        ).pack(side="left", padx=10)

        ttk.Button(
            header,
            text="윈들리 정보입력",
            command=lambda: threading.Thread(
                target=self.upload_to_windly,
                daemon=True
            ).start()
        ).pack(side="left", padx=10)

        # ===============================
        # 리스트 영역
        # ===============================
        self.list_container = ttk.Frame(self.frame)
        self.list_container.pack(fill="both", expand=True, padx=10, pady=10)

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
    # 선택된 아이템
    # ==========================================================
    def get_checked_items(self):
        items = [
            p for p in self.app.products_collected
            if getattr(p, "checked", False)
        ]
        if not items:
            messagebox.showwarning(
                "알림",
                "선택된 상품이 없습니다.",
                parent=self.app.root
            )
            return []
        return items

    # ==========================================================
    # 리스트 갱신
    # ==========================================================
    def refresh(self):

        for w in self.list_container.winfo_children():
            w.destroy()

        for idx, item in enumerate(self.app.products_collected, start=1):
            row = ttk.Frame(self.list_container)
            row.pack(fill="x", pady=7)

            # 개별 체크박스
            var = tk.BooleanVar(value=getattr(item, "checked", True))

            def on_toggle(v=var, it=item):
                it.checked = v.get()
                all_checked = bool(self.app.products_collected) and all(
                    p.checked for p in self.app.products_collected
                )
                self.select_all_var.set(all_checked)

            ttk.Checkbutton(
                row,
                variable=var,
                command=on_toggle
            ).pack(side="left", padx=(5, 5))

            # 구분선
            sep = tk.Frame(
                self.list_container,
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

            # 썸네일
            thumb_label = ttk.Label(row, text="[로딩중]")
            thumb_label.pack(side="left", padx=5)

            def cb(img, lbl=thumb_label):
                if img:
                    lbl.config(image=img, text="")
                    lbl.image = img
                else:
                    lbl.config(text="[오류]")

            if getattr(item, "make_thumbnail_img", None) and os.path.exists(item.make_thumbnail_img):
                load_local_image_async(item.make_thumbnail_img, (140, 140), cb, self.app.root)
            elif getattr(item, "thumbnail_url", None):
                load_image_async(item.thumbnail_url, (140, 140), cb, self.app.root)
            else:
                thumb_label.config(text="[없음]")

            # 텍스트 블록
            text_block = ttk.Frame(row)
            text_block.pack(side="left", padx=10, fill="x")

            ttk.Label(
                text_block,
                text=item.final_name or "(상품명)",
                font=("맑은 고딕", 11, "bold")
            ).pack(anchor="w")

            # 카테고리 표시
            template_key = getattr(item, "matched_category_template_key", None)
            category_name = getattr(item, "category_name", None)

            if template_key or category_name:
                cat_row = ttk.Frame(text_block)
                cat_row.pack(anchor="w", pady=(1, 0))

                if template_key:
                    ttk.Label(
                        cat_row,
                        text=template_key,
                        foreground="#777",
                        font=("맑은 고딕", 9)
                    ).pack(side="left")

                if template_key and category_name:
                    ttk.Label(
                        cat_row,
                        text="  |  ",
                        foreground="#aaa",
                        font=("맑은 고딕", 9)
                    ).pack(side="left")

                if category_name:
                    ttk.Label(
                        cat_row,
                        text=category_name,
                        foreground="#1a73e8",
                        font=("맑은 고딕", 10)
                    ).pack(side="left")

            # 상태 표시
            status_frame = ttk.Frame(text_block)
            status_frame.pack(anchor="w", pady=(2, 0))

            def color(v):
                return "green" if v == "성공" else ("red" if v == "실패" else "gray")

            n = getattr(item, "naver_status", "미등록")
            w = getattr(item, "windly_status", "미등록")

            thumb_cfg = "완료" if getattr(item, "thumbnail_job", None) else "미설정"
            thumb_color = "green" if getattr(item, "thumbnail_job", None) else "gray"

            ttk.Label(
                status_frame,
                text=f"썸네일설정: {thumb_cfg}",
                foreground=thumb_color
            ).pack(side="left", padx=(0, 10))

            ttk.Label(
                status_frame,
                text=f"네이버: {n}",
                foreground=color(n)
            ).pack(side="left", padx=(0, 10))

            ttk.Label(
                status_frame,
                text=f"윈들리: {w}",
                foreground=color(w)
            ).pack(side="left")

            # 버튼
            ttk.Button(
                row,
                text="삭제",
                command=lambda p=item: self.delete_item(p)
            ).pack(side="right")

            ttk.Button(
                row,
                text="상세보기",
                command=lambda p=item: open_detail_window(
                    self.app.root,
                    p,
                    self.refresh
                )
            ).pack(side="right", padx=5)

    # ==========================================================
    # 삭제
    # ==========================================================
    def delete_item(self, item):
        if item in self.app.products_collected:
            self.app.products_collected.remove(item)
            self.refresh()

    # ==========================================================
    # 썸네일 생성
    # ==========================================================
    def generate_all_thumbnails(self):
        from image_tools.thumbnail_runner import run_thumbnail_job
        import traceback

        items = self.get_checked_items()
        if not items:
            return

        total = len(items)
        done = 0
        failed = 0

        for item in items:
            job = getattr(item, "thumbnail_job", None)
            if not job:
                continue

            try:
                ok, out_path = run_thumbnail_job(job)
                if ok and out_path:
                    item.make_thumbnail_img = out_path
                    job.status = "done"
                    done += 1
                else:
                    job.status = "failed"
                    failed += 1
            except Exception:
                traceback.print_exc()
                job.status = "failed"
                failed += 1

            self.refresh()
            time.sleep(0.1)

        messagebox.showinfo(
            "썸네일 생성 완료",
            f"총 {total}개\n성공: {done}\n실패: {failed}"
        )

    # ==========================================================
    # 네이버 업로드
    # ==========================================================
    def upload_to_naver(self):
        from naver_uploader import NaverUploader

        items = self.get_checked_items()
        if not items:
            return

        uploader = NaverUploader()
        total = len(items)
        success = 0
        failed = []

        for item in items:
            try:
                ok = uploader.run_for_item(item)
                item.naver_status = "성공" if ok else "실패"
                if ok:
                    success += 1
                else:
                    failed.append(item.final_name or item.url)
            except Exception:
                item.naver_status = "실패"
                failed.append(item.final_name or item.url)

            self.app.upload_status_label_global.config(
                text=f"네이버: {success}/{total} 진행중 (실패 {len(failed)})"
            )
            self.refresh()

        messagebox.showinfo(
            "네이버 업로드 완료",
            f"총 {total}개 중 {success} 성공 / {len(failed)} 실패"
        )

    # ==========================================================
    # Windly 업로드
    # ==========================================================
    def upload_to_windly(self):
        from automation.windly.uploader import WindlyUploader
        from automation.windly_config_loader import load_windly_config

        items = self.get_checked_items()
        if not items:
            return

        user_id, user_pw = load_windly_config()
        total = len(items)
        success = 0
        failed = []

        for item in items:
            uploader = WindlyUploader(user_id, user_pw)
            try:
                ok = uploader.run_for_item(item)
                item.windly_status = "성공" if ok else "실패"
                if ok:
                    success += 1
                else:
                    failed.append(item.final_name or item.url)
            except Exception:
                item.windly_status = "실패"
                failed.append(item.final_name or item.url)

            self.app.upload_status_label_global.config(
                text=f"윈들리: {success}/{total} 진행중 (실패 {len(failed)})"
            )
            self.refresh()
            time.sleep(0.4)

        messagebox.showinfo(
            "윈들리 입력 완료",
            f"총 {total}개 중 {success} 성공 / {len(failed)} 실패"
        )
