# gui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from scrapers.scraper_manager import ScraperManager
from image_tools.image_utils import clean_temp_all
from gui.styles.ttk_styles import setup_ttk_styles

from config.smartstore_config import load_smartstore_config
from category.attributes.smartstore_login import login_and_create_session

# pages
from gui.pages.collect_page import CollectPage
from gui.pages.collected_page import CollectedPage
from gui.pages.naver_best_page import NaverBestPage
from gui.pages.extra_page import ExtraPage
from gui.pages.settings_page import SettingsPage
from PIL import Image, ImageTk
import os

APP_VERSION = "v2.1.0"
HEADER_HEIGHT = 80


class ProductCollectorGUI:
    def __init__(self, root):
        self.root = root
        setup_ttk_styles(root)
        self.root.title("soeasy 상품 수집기")

        # ===============================
        # 전역 상태
        # ===============================
        self.scraper = ScraperManager()
        self.smartstore_session = None

        self.products_pending = []
        self.products_collected = []

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 수집된 베스트 상품 데이터를 저장할 리스트
        self.naver_best_items = []

        self.build_ui()

    # ==========================================================
    # UI 구성
    # ==========================================================
    def build_ui(self):

        # ===============================
        # 전체 메인 컨테이너
        # ===============================
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # ===============================
        # 왼쪽 메뉴 (최상단~최하단)
        # ===============================
        self.sidebar = ttk.Frame(main, width=160)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # -------------------------------
        # 세로 구분선
        # -------------------------------
        tk.Frame(
            main,
            width=1,
            bg="#dcdcdc"
        ).pack(side="left", fill="y")

        # ===============================
        # 오른쪽 영역 (헤더 + 콘텐츠)
        # ===============================
        right_area = ttk.Frame(main)
        right_area.pack(side="left", fill="both", expand=True)

        # -------------------------------
        # 상단 헤더 (오른쪽만)
        # -------------------------------
        header = ttk.Frame(right_area, height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        self.header_title = ttk.Label(
            header,
            text="상품 수집",
            font=("맑은 고딕", 13, "bold")
        )
        self.header_title.pack(side="left", padx=12)

        self.upload_status_label_global = ttk.Label(
            header,
            text="대기중",
            foreground="blue",
            font=("맑은 고딕", 11)
        )
        self.upload_status_label_global.pack(side="right", padx=12)

        # -------------------------------
        # 헤더 하단 가로 구분선 (오른쪽만)
        # -------------------------------
        tk.Frame(
            right_area,
            height=1,
            bg="#dcdcdc"
        ).pack(fill="x")

        # -------------------------------
        # 콘텐츠 영역
        # -------------------------------
        self.content = ttk.Frame(right_area)
        self.content.pack(fill="both", expand=True)

        # ===============================
        # 페이지 초기화
        # ===============================
        self.pages = {
            "collect": CollectPage(self.content, self),
            "naver_best": NaverBestPage(self.content, self),
            "collected": CollectedPage(self.content, self),
            "extra": ExtraPage(self.content, self),
            "settings": SettingsPage(self.content, self),
        }

        for page in self.pages.values():
            page.build()
            
        # ===============================
        # 사이드바 상단 로고 영역
        # ===============================
        logo_area = ttk.Frame(self.sidebar)
        logo_area.pack(fill="x", pady=(6, 8))

        # 로고 이미지 로드
        logo_path = os.path.join("images", "logo.png")

        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            self.logo_img = ImageTk.PhotoImage(img)  # GC 방지용 self 참조

            logo_label = ttk.Label(
                logo_area,
                image=self.logo_img
            )
            logo_label.pack(anchor="center", pady=(2, 2))
        else:
            # fallback 텍스트 (이미지 없을 경우)
            ttk.Label(
                logo_area,
                text="Soeasy",
                font=("Segoe UI", 16, "bold")
            ).pack(anchor="center")
            
        ttk.Label(
            logo_area,
            text=APP_VERSION,
            font=("Segoe UI", 9),
            foreground="#888888"
        ).pack(anchor="center", pady=(0, 4))    

        # -------------------------------
        # 사이드바 상단 구분선
        # -------------------------------
        tk.Frame(
            self.sidebar,
            height=1,
            bg="#dcdcdc"
        ).pack(fill="x")


        # ===============================
        # 왼쪽 메뉴 버튼
        # ===============================
        def menu(text, key):
            ttk.Button(
                self.sidebar,
                text=text,
                command=lambda: self.show_page(key)
            ).pack(fill="x", padx=10, pady=6)

        menu("상품 수집", "collect")
        menu("네이버 상품 수집", "naver_best")
        menu("수집 완료", "collected")
        menu("부가기능", "extra")
        menu("설정", "settings")

        # 기본 페이지
        self.show_page("collect")

    # ==========================================================
    # 페이지 전환
    # ==========================================================
    def show_page(self, key):
        for page in self.pages.values():
            page.hide()
        self.pages[key].show()

        title_map = {
            "collect": "상품 수집",
            "naver_best": "네이버 상품 수집",
            "collected": "수집 상품",
            "extra": "부가기능",
            "settings": "설정",
        }
        self.header_title.config(text=title_map.get(key, ""))

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

            for item in list(self.products_pending):
                try:
                    result = self.scraper.collect(item.url)
                    if "error" in result:
                        failed.append(item.url)
                        continue

                    item.load_data(result)

                    item.collect_status = "완료"
                    if item not in self.products_collected:
                        self.products_collected.append(item)

                    success += 1

                except Exception:
                    failed.append(item.url)

                self.upload_status_label_global.config(
                    text=f"수집 {success}/{total} (실패 {len(failed)})"
                )

                self.pages["collect"].refresh()
                self.pages["collected"].refresh()

            messagebox.showinfo(
                "수집 완료",
                f"총 {total}개 중 {success} 성공 / {len(failed)} 실패"
            )

        threading.Thread(target=task, daemon=True).start()

    # ==========================================================
    # SmartStore 세션
    # ==========================================================
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
    # 종료 처리
    # ==========================================================
    def on_close(self):
        if messagebox.askokcancel("프로그램 종료", "Soeasy2 상품 수집기를 종료하시겠습니까?"):
            self.root.destroy()


# ==========================================================
# 실행
# ==========================================================
def run_gui():
    clean_temp_all()
    root = tk.Tk()
    root.geometry("1400x800")
    app = ProductCollectorGUI(root)
    root.app = app
    root.mainloop()
