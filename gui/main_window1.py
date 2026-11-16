# gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import time, threading, os
from datetime import datetime

from models.product_item import ProductItem
from scrapers.scraper_manager import ScraperManager
from gui.product_detail.detail_window import open_detail_window
from gui.styles.ttk_styles import setup_ttk_styles
from gui.widgets.image_loader import load_image_async, load_local_image_async   # async loader 필수 임포트
from image_tools.image_utils import clean_temp_all
from gui.widgets.center_popup import CenterPopup
from config.smartstore_config import load_smartstore_config
from category.attributes.smartstore_login import login_and_create_session
from automation.windly.windly_category_collector import main as windly_category_collect_main



class ProductCollectorGUI:
    def __init__(self, root):
        self.root = root
        setup_ttk_styles(root)
        self.root.title("Soeasy 상품 수집기")

        self.smartstore_session = None
        self.scraper = ScraperManager()

        self.products_pending = []       # 탭1: 수집 대기
        self.products_collected = []     # 탭2: 수집 완료

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()


    # ==========================================================
    # UI 구성
    # ==========================================================
    def build_ui(self):

        # 상단 상태바 프레임
        top_status = ttk.Frame(self.root)
        top_status.pack(fill="x", pady=3, padx=10)

        # 🔥 윈들리 카테고리 수집 버튼 (오른쪽)
        ttk.Button(
            top_status,
            text="윈들리 카테고리 수집",
            command=self.run_windly_category_collect
        ).pack(side="right", padx=(6, 0))

        # 진행상황 라벨 (버튼 왼쪽에 붙음)
        self.upload_status_label_global = ttk.Label(
            top_status,
            text="대기중",
            foreground="blue",
            font=("맑은 고딕", 11)
        )
        self.upload_status_label_global.pack(side="right")


        # Notebook 생성
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)

        self.tab_pending   = ttk.Frame(self.nb)
        self.tab_collected = ttk.Frame(self.nb)

        self.nb.add(self.tab_pending,   text="상품수집 (0)")
        self.nb.add(self.tab_collected, text="수집완료 (0)")

        self.build_tab_pending()
        self.build_tab_collected()
    

    # ==========================================================
    # 탭1 : 상품 수집 대기
    # ==========================================================
    def build_tab_pending(self):
        
        top = ttk.Frame(self.tab_pending)
        top.pack(fill="x", padx=10, pady=10)
        
        def show_supported_sites():
            popup = CenterPopup(
                parent=self.root,
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
        
        # URL 입력창
        self.url_entry = ttk.Entry(top)
        self.url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(top, text="추가하기", command=self.add_product).pack(side="left", padx=5)
        ttk.Button(top, text="정보수집하기", command=self.collect_all).pack(side="left", padx=5)

        self.pending_frame = ttk.Frame(self.tab_pending)
        self.pending_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh_tab_pending()


    def run_windly_category_collect(self):
        """
        윈들리 카테고리 수집 main() 실행
        GUI 멈춤 방지를 위해 thread 사용
        """

        def task():
            try:
                self.root.after(0, lambda: self.upload_status_label_global.config(
                    text="윈들리 카테고리 수집 중..."
                ))

                windly_category_collect_main()

                self.root.after(0, lambda: self.upload_status_label_global.config(
                    text="윈들리 카테고리 수집 완료"
                ))

                self.root.after(0, lambda: messagebox.showinfo(
                    "완료",
                    "윈들리 카테고리 수집이 완료되었습니다."
                ))

            except Exception as e:
                print("[WINDLY CATEGORY ERROR]", repr(e))

                self.root.after(0, lambda: self.upload_status_label_global.config(
                    text="윈들리 카테고리 수집 실패"
                ))

                self.root.after(0, lambda: messagebox.showerror(
                    "오류",
                    f"윈들리 카테고리 수집 중 오류 발생\n\n{e}"
                ))

        threading.Thread(target=task, daemon=True).start()

    
    # ==========================================================
    # 탭2 : 수집 완료
    # ==========================================================
    def build_tab_collected(self):

        self.collected_frame = ttk.Frame(self.tab_collected)
        self.collected_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header = ttk.Frame(self.collected_frame)
        header.pack(fill="x", pady=5)
        
        # ===============================
        # 전체 선택 체크박스
        # ===============================
        self.select_all_var = tk.BooleanVar(value=True)

        def toggle_select_all():
            val = self.select_all_var.get()
            for item in self.products_collected:
                item.checked = val
            self.refresh_tab_collected()

        ttk.Checkbutton(
            header,
            text="전체 선택",
            variable=self.select_all_var,
            command=toggle_select_all
        ).pack(side="left", padx=10)
        
        # ------------------------------------------------------
        # 썸네일 생성 버튼
        # ------------------------------------------------------
        ttk.Button(header, text="썸네일 생성",
            command=lambda: threading.Thread(target=self.generate_all_thumbnails, daemon=True).start()
        ).pack(side="left", padx=10)

        # ------------------------------------------------------
        # 네이버 업로드 버튼
        # ------------------------------------------------------
        ttk.Button(header, text="네이버 상품등록",
            command=lambda: threading.Thread(target=self.upload_to_naver, daemon=True).start()
        ).pack(side="left", padx=10)

        # ------------------------------------------------------
        # Windly 업로드 버튼
        # ------------------------------------------------------
        ttk.Button(header, text="윈들리 정보입력",
            command=lambda: threading.Thread(target=self.upload_to_windly, daemon=True).start()
        ).pack(side="left", padx=10)

        # 리스트 표시 영역
        self.list_container = ttk.Frame(self.collected_frame)
        self.list_container.pack(fill="both", expand=True)

        self.refresh_tab_collected()


    # ==========================================================
    # 공통: 탭 제목 갱신
    # ==========================================================
    def update_tab_titles(self):
        self.nb.tab(0, text=f"상품수집 ({len(self.products_pending)})")
        self.nb.tab(1, text=f"수집완료 ({len(self.products_collected)})")


    # ==========================================================
    # 탭1 업데이트
    # ==========================================================
    def refresh_tab_pending(self):
        
        for w in self.pending_frame.winfo_children():
            w.destroy()

        for idx, item in enumerate(self.products_pending, start=1):
            row = ttk.Frame(self.pending_frame)
            row.pack(fill="x", pady=6)
            
            sep = tk.Frame(
                self.pending_frame,
                height=1,
                bg="#e6e6e6"   # 아주 연한 회색
            )
            sep.pack(fill="x", padx=5, pady=(0, 3))

            # 🔢 번호
            ttk.Label(
                row,
                text=f"{idx}.",
                width=4,
                anchor="e",
                foreground="#555",
                font=("맑은 고딕", 13, "bold")
            ).pack(side="left", padx=(0,5))

            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            ttk.Label(
                text_frame,
                text=item.url,
                font=("맑은 고딕", 10, "bold")
            ).pack(anchor="w")

            status = getattr(item, "collect_status", "대기")
            color  = "green" if status == "완료" else "gray"

            ttk.Label(
                text_frame,
                text=f"수집: {status}",
                foreground=color
            ).pack(anchor="w")

            side = ttk.Frame(row)
            side.pack(side="right")

            ttk.Label(
                side,
                text=item.added_at,
                foreground="#666"
            ).pack(side="left", padx=(0,10))

            ttk.Button(
                side,
                text="삭제",
                command=lambda p=item: self.delete_pending(p)
            ).pack(side="left")

        self.update_tab_titles()

    def get_checked_items(self):
        items = [p for p in self.products_collected if getattr(p, "checked", False)]
        if not items:
            messagebox.showwarning("알림", "선택된 상품이 없습니다.", parent=self.root)
            return []
        return items

    # ==========================================================
    # 탭2 업데이트
    # ==========================================================
    def refresh_tab_collected(self):
    
        for w in self.list_container.winfo_children():
            w.destroy()

        for idx, item in enumerate(self.products_collected, start=1):
            row = ttk.Frame(self.list_container)
            row.pack(fill="x", pady=7)
            
            # ===============================
            # 개별 체크박스
            # ===============================
            var = tk.BooleanVar(value=item.checked)

            def on_toggle(v=var, it=item):
                it.checked = v.get()

                # 전체선택 상태 동기화
                all_checked = bool(self.products_collected) and all(
                    p.checked for p in self.products_collected
                )
                self.select_all_var.set(all_checked)

            ttk.Checkbutton(
                row,
                variable=var,
                command=on_toggle
            ).pack(side="left", padx=(5, 5))
            
            sep = tk.Frame(
                self.list_container,
                height=1,
                bg="#e6e6e6"   # 아주 연한 회색
            )
            sep.pack(fill="x", padx=5, pady=(0, 3))

            # 🔢 번호
            ttk.Label(
                row,
                text=f"{idx}.",
                width=4,
                anchor="e",
                foreground="#555",
                font=("맑은 고딕", 13, "bold")
            ).pack(side="left", padx=(0,5))

            # ----------------------------
            # 썸네일 표시
            # ----------------------------
            thumb_label = ttk.Label(row, text="[로딩중]")
            thumb_label.pack(side="left", padx=5)

            def cb(img, lbl=thumb_label):
                if img:
                    lbl.config(image=img, text="")
                    lbl.image = img
                else:
                    lbl.config(text="[오류]")

            if item.make_thumbnail_img and os.path.exists(item.make_thumbnail_img):
                load_local_image_async(item.make_thumbnail_img, (140, 140), cb, self.root)

            elif item.thumbnail_url:
                load_image_async(item.thumbnail_url, (140, 140), cb, self.root)

            else:
                thumb_label.config(text="[없음]")

            text_block = ttk.Frame(row)
            text_block.pack(side="left", padx=10, fill="x")

            # ----------------------------
            # 상품명 (윗줄)
            # ----------------------------
            ttk.Label(
                text_block,
                text=item.final_name or "(상품명)",
                font=("맑은 고딕", 11, "bold")
            ).pack(anchor="w")

            # ----------------------------
            # 카테고리 표시 (template_key + category)
            # ----------------------------
            template_key = getattr(item, "matched_category_template_key", None)
            category_name = getattr(item, "category_name", None)

            if template_key or category_name:
                cat_row = ttk.Frame(text_block)
                cat_row.pack(anchor="w", pady=(1, 0))

                # 왼쪽: template_key
                if template_key:
                    ttk.Label(
                        cat_row,
                        text=template_key,
                        foreground="#777",
                        font=("맑은 고딕", 9)
                    ).pack(side="left")

                # 구분자
                if template_key and category_name:
                    ttk.Label(
                        cat_row,
                        text="  |  ",
                        foreground="#aaa",
                        font=("맑은 고딕", 9)
                    ).pack(side="left")

                # 오른쪽: category_name
                if category_name:
                    ttk.Label(
                        cat_row,
                        text=category_name,
                        foreground="#1a73e8",
                        font=("맑은 고딕", 10)
                    ).pack(side="left")


            # ----------------------------
            # 상태 표시 (아랫줄)
            # ----------------------------
            status_frame = ttk.Frame(text_block)
            status_frame.pack(anchor="w", pady=(2, 0))

            def color(v):
                return "green" if v == "성공" else ("red" if v == "실패" else "gray")

            n = getattr(item, "naver_status", "미등록")
            w = getattr(item, "windly_status", "미등록")

            # 썸네일 설정 상태
            thumb_cfg = "미설정"
            thumb_color = "gray"

            if getattr(item, "thumbnail_job", None):
                thumb_cfg = "완료"
                thumb_color = "green"

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

            # ----------------------------
            # 버튼
            # ----------------------------
            ttk.Button(
                row,
                text="삭제",
                command=lambda p=item: self.delete_collected(p)
            ).pack(side="right")

            ttk.Button(
                row,
                text="상세보기",
                command=lambda p=item: open_detail_window(self.root, p, self.refresh_tab_collected)
            ).pack(side="right", padx=5)

        self.update_tab_titles()



    # ==========================================================
    # 상품 추가
    # ==========================================================
    def add_product(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("알림", "URL을 입력해 주세요.")
            return

        item = ProductItem(url)
        item.added_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.products_pending.append(item)
        self.url_entry.delete(0, tk.END)
        self.refresh_tab_pending()


    # ==========================================================
    # 삭제
    # ==========================================================
    def delete_pending(self, item):
        self.products_pending.remove(item)
        self.refresh_tab_pending()

    def delete_collected(self, item):
        self.products_collected.remove(item)
        self.refresh_tab_collected()


    def generate_all_thumbnails(self):
        """
        수집완료 리스트의 모든 상품에 대해
        thumbnail_job 이 있는 경우 일괄 썸네일 생성
        """

        import time
        import traceback
        from image_tools.thumbnail_runner import run_thumbnail_job

        total = len(self.products_collected)
        print(f"[THUMB][ALL] total items = {total}")

        if total == 0:
            print("[THUMB][ALL] no products")
            return

        done = 0
        failed = 0

        items = self.get_checked_items()
        if not items:
            return

        for idx, item in enumerate(items):
            print("=" * 60)
            print(f"[THUMB][ITEM {idx}] id={item.item_id}")

            job = getattr(item, "thumbnail_job", None)
            if not job:
                print("[THUMB][SKIP] no thumbnail_job")
                continue

            try:
                print("[THUMB][JOB] template =", job.config.template)
                print("[THUMB][JOB] image_urls =", job.config.image_urls)
                print("[THUMB][JOB] ext_state =", job.config.ext_state)

                ok, out_path = run_thumbnail_job(job)

                print("[THUMB][RESULT] ok =", ok)
                print("[THUMB][RESULT] out_path =", out_path)

                if ok and out_path:
                    item.make_thumbnail_img = out_path
                    job.status = "done"
                    done += 1
                else:
                    job.status = "failed"
                    failed += 1

            except Exception as e:
                print("[THUMB][ERROR] exception occurred")
                traceback.print_exc()

                job.status = "failed"
                job.error = str(e)
                failed += 1

            self.refresh_tab_collected()
            time.sleep(0.1)

        print("=" * 60)
        print(f"[THUMB][SUMMARY] total={total} success={done} failed={failed}")

        messagebox.showinfo(
            "썸네일 생성 완료",
            f"총 {total}개\n성공: {done}\n실패: {failed}"
        )



    # ==========================================================
    # 네이버 업로드
    # ==========================================================
    def upload_to_naver(self):
        import threading
        from naver_uploader import NaverUploader

        items = self.get_checked_items()
        if not items:
            return

        total = len(items)
        if total == 0:
            messagebox.showwarning("알림", "등록할 상품이 없습니다.")
            return

        def task():
            uploader = NaverUploader()
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

                except Exception as e:
                    print("[NAVER ERROR]", repr(e))
                    item.naver_status = "실패"
                    failed.append(item.final_name or item.url)

                # 🔥 UI 갱신은 after()로
                self.root.after(0, lambda s=success, f=len(failed): (
                    self.upload_status_label_global.config(
                        text=f"네이버: {s}/{total} 진행중 (실패 {f})"
                    ),
                    self.refresh_tab_collected()
                ))

            self.root.after(0, lambda: (
                messagebox.showinfo(
                    "네이버 업로드 완료",
                    f"총 {total}개 중 {success} 성공 / {len(failed)} 실패"
                ),
                self.upload_status_label_global.config(
                    text=f"네이버 완료: {success}/{total}, 실패 {len(failed)}"
                )
            ))

        threading.Thread(target=task, daemon=True).start()


    # ==========================================================
    # Windly 업로드
    # ==========================================================
    def upload_to_windly(self):
        from automation.windly.uploader import WindlyUploader
        from automation.windly_config_loader import load_windly_config
        import time
        from tkinter import messagebox

        items = self.get_checked_items()
        if not items:
            return

        user_id, user_pw = load_windly_config()

        total = len(items)
        if total == 0:
            messagebox.showwarning("알림", "윈들리에 입력할 상품이 없습니다.")
            return

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

            self.upload_status_label_global.config(
                text=f"윈들리: {success}/{total} 진행중 (실패 {len(failed)})"
            )
            self.refresh_tab_collected()
            time.sleep(0.4)

        messagebox.showinfo(
            "윈들리 입력 완료",
            f"총 {total}개 중 {success} 성공 / {len(failed)} 실패"
        )

        self.upload_status_label_global.config(
            text=f"윈들리 완료: {success}/{total}, 실패 {len(failed)}"
        )



    # ==========================================================
    # 전체 정보 수집
    # ==========================================================
    def collect_all(self):

        if not self.products_pending:
            messagebox.showinfo("알림", "수집할 상품이 없습니다.")
            return
        
        try:
            self.smartstore_session = self.ensure_smartstore_session()
        except Exception as e:
            messagebox.showerror("로그인 실패", str(e))
            return
        
        self.upload_status_label_global.config(text="수집 시작")

        def task():

            total = len(self.products_pending)
            success = 0
            failed = []

            for idx, item in enumerate(list(self.products_pending), start=1):

                try:
                    result = self.scraper.collect(item.url)

                    if "error" in result:
                        failed.append(item.url)
                        continue

                    item.load_data(result)
                    
                    # 카테고리 기반 속성 프리패치
                    if item.category_code:
                        from category.services.attribute_prefetch import prefetch_category_attributes

                        prefetch_category_attributes(
                            item=item,
                            session=self.smartstore_session,
                            product_name=item.final_name,
                            option_names=[
                                v.get("name")
                                for opt in item.parsed_raw.get("options", [])
                                for v in opt.get("values", [])
                                if v.get("name")
                            ],
                            detail_text=item.final_detail_text,
                            image_urls=[item.thumbnail_url] if item.thumbnail_url else [],
                        )

                    item.collect_status = "완료"

                    if item not in self.products_collected:
                        self.products_collected.append(item)

                    success += 1

                except Exception:
                    import traceback
                    print("[COLLECT ERROR]", item.url)
                    traceback.print_exc()
                    failed.append(item.url)

                self.upload_status_label_global.config(
                    text=f"수집 {success}/{total} (실패 {len(failed)})"
                )

                self.refresh_tab_pending()
                self.refresh_tab_collected()
                time.sleep(0.2)

            messagebox.showinfo(
                "수집 완료",
                f"총 {total}개 중 {success} 성공 / {len(failed)} 실패"
            )

        threading.Thread(target=task, daemon=True).start()
        
    def ensure_smartstore_session(self):
        if self.smartstore_session:
            return self.smartstore_session

        cfg = load_smartstore_config()

        session = login_and_create_session(
            naver_id=cfg["naver_id"],
            naver_pw=cfg["naver_pw"],
            headless=cfg.get("headless", False),
        )

        self.smartstore_session = session
        return session


    # ==========================================================
    # 종료 처리 (메시지 박스 추가)
    # ==========================================================
    def on_close(self):
        """
        X 버튼 또는 종료 호출 시 사용자에게 확인을 요청합니다.
        """
        if messagebox.askokcancel("프로그램 종료", "Soeasy2 상품 수집기를 종료하시겠습니까?"):
            # 임시 파일 정리 등 종료 전 필요한 작업이 있다면 여기에 추가 가능
            print("[GUI] 프로그램 종료 중...")
            self.root.destroy()


# 실행
def run_gui():
    clean_temp_all()
    
    root = tk.Tk()
    root.geometry("1400x800")
    app = ProductCollectorGUI(root)
    root.app = app
    root.mainloop()
