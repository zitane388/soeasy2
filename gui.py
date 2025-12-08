# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk
import io, os, tempfile, subprocess
import threading, time, json, urllib
import base64
from websocket import create_connection
from datetime import datetime

from models import ProductItem
from scrapers.scraper_manager import ScraperManager
from utils.detail_description_generator import generate_detail_html


# ==========================================================
# 전역 이미지 캐시
# ==========================================================
IMAGE_CACHE = {}      # { url: PhotoImage }
BASE64_CACHE = {}     # { base64_str: PhotoImage }

def resize_aspect_fit(img, target_size):
    tw, th = target_size
    iw, ih = img.size

    # 1) 비율 유지한 채 맞는 크기로 축소/확대
    scale = min(tw / iw, th / ih)
    new_size = (int(iw * scale), int(ih * scale))
    resized = img.resize(new_size, Image.LANCZOS)

    # 2) 새 캔버스(배경) 생성
    canvas = Image.new("RGBA", (tw, th), (255, 255, 255, 0))

    # 3) 중앙 정렬
    left = (tw - new_size[0]) // 2
    top = (th - new_size[1]) // 2
    canvas.paste(resized, (left, top))

    return canvas

# ==========================================================
# 동기 다운로드 + 캐싱
# ==========================================================
def get_cached_image(url, size=(160, 160), disable_cache=False):
    key = (url, size)

    # 1) 캐시 사용 여부 확인
    if not disable_cache and key in IMAGE_CACHE:
        return IMAGE_CACHE[key]

    try:
        resp = requests.get(url, timeout=5)
        raw_img = Image.open(io.BytesIO(resp.content))

        img = resize_aspect_fit(raw_img, size)
        tki = ImageTk.PhotoImage(img)

        # 2) disable_cache=True → 캐시에 저장하지 않음
        if not disable_cache:
            IMAGE_CACHE[key] = tki

        return tki

    except Exception:
        return None


def get_cached_image_base64(data, size=(40, 40)):
    key = (data, size)

    if key in BASE64_CACHE:
        return BASE64_CACHE[key]

    try:
        raw = base64.b64decode(data.split(",")[-1])
        raw_img = Image.open(io.BytesIO(raw))
        img = resize_aspect_fit(raw_img, size)   # <<< 여기!!
        tki = ImageTk.PhotoImage(img)
        BASE64_CACHE[key] = tki
        return tki
    except:
        return None

# ==========================================================
# 비동기 이미지 로더
# ==========================================================
def load_image_async(url, size, callback, root, disable_cache=False):
    if not disable_cache and url in IMAGE_CACHE:
        root.after(0, lambda: callback(IMAGE_CACHE[url]))
        return
    def task():
        img = get_cached_image(url, size, disable_cache=disable_cache)
        root.after(0, lambda: callback(img))   # UI thread
    threading.Thread(target=task, daemon=True).start()


def load_base64_async(data, size, callback, root):
    def task():
        img = get_cached_image_base64(data, size)
        root.after(0, lambda: callback(img))   # UI thread
    threading.Thread(target=task, daemon=True).start()

def bind_mousewheel(widget, target_canvas):
    def _on_mousewheel(event):
        # Windows
        target_canvas.yview_scroll(-1 * int(event.delta / 120), "units")
    widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", _on_mousewheel))
    widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))
                
# ===================================================================
# GUI 메인
# ===================================================================
class ProductCollectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Soeasy2 상품 수집기")

        # Scraper
        self.scraper = ScraperManager()

        # 데이터 저장
        self.products_pending = []        # 탭1 (수집대기)
        self.products_collected = []      # 탭2 (수집완료)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()


    # ==============================================================
    # UI 구성
    # ==============================================================
    def build_ui(self):
        
        # 📌 전역 진행상황 라벨 (모든 탭에서 사용 가능)
        self.upload_status_label_global = ttk.Label(
            self.root, text="대기중", foreground="blue", font=("맑은 고딕", 11)
        )
        self.upload_status_label_global.pack(anchor="ne", pady=3, padx=10)

        # 📌 Notebook → grid 삭제, pack으로 교체
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)     # ← 여기만 바뀌면 해결

        # 탭 생성
        self.tab_pending = ttk.Frame(self.nb)
        self.tab_collected = ttk.Frame(self.nb)

        self.nb.add(self.tab_pending, text="상품수집 (0)")
        self.nb.add(self.tab_collected, text="수집완료 (0)")

        self.build_tab_pending()
        self.build_tab_collected()


    # ==============================================================
    # 탭 1
    # ==============================================================
    def build_tab_pending(self):

        top = ttk.Frame(self.tab_pending)
        top.pack(fill="x", padx=10, pady=10)

        self.url_entry = ttk.Entry(top)
        self.url_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(top, text="추가하기",
                   command=self.add_product).pack(side="left", padx=5)

        ttk.Button(top, text="정보수집하기",
                   command=self.collect_all).pack(side="left", padx=5)

        self.pending_frame = ttk.Frame(self.tab_pending)
        self.pending_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh_tab_pending()


    # ==============================================================
    # 탭 2
    # ==============================================================
    def build_tab_collected(self):
        self.collected_frame = ttk.Frame(self.tab_collected)
        self.collected_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ------------------------------------------------
        # 상단 헤더 + 상태 라벨 (공용)
        # ------------------------------------------------
        header = ttk.Frame(self.collected_frame)
        header.pack(fill="x", pady=5)

        # ==========================================================
        # 🔹 네이버 업로드 Thread
        # ==========================================================
        def upload_to_naver_thread():
    
            from naver_uploader import NaverUploader
            uploader = NaverUploader()

            total = len(self.products_collected)
            if total == 0:
                messagebox.showwarning("알림", "등록할 상품이 없습니다.")
                return

            success = 0
            failed = []

            self.upload_status_label_global.config(text=f"네이버 등록: 0/{total} 시작")

            for item in self.products_collected:
                try:
                    ok = uploader.run_for_item(item)

                    # <<< 🔥 여기서 상태 업데이트
                    item.naver_status = "성공" if ok else "실패"
                    self.refresh_tab_collected()

                    if ok:
                        success += 1
                        self.upload_status_label_global.config(text=f"네이버 등록: {success}/{total} 진행중")
                    else:
                        failed.append(item.final_name or item.url)
                        self.upload_status_label_global.config(
                            text=f"네이버 등록: {success}/{total} 진행중 (실패 {len(failed)})"
                        )

                except Exception as e:
                    item.naver_status = "실패"   # 예외 발생도 실패 처리
                    failed.append(item.final_name or item.url)
                    print("[NAVER UPLOAD ERROR]", e)
                    self.upload_status_label_global.config(
                        text=f"네이버 등록: {success}/{total} 진행중 (실패 {len(failed)})"
                    )

                self.root.update_idletasks()
                time.sleep(0.35)

            # 결과 팝업
            fail_count = len(failed)
            messagebox.showinfo(
                "네이버 업로드 결과",
                f"총 {total}개 중 {success}개 완료\n실패 {fail_count}개\n"
            )
            self.upload_status_label_global.config(text=f"네이버 등록 완료: {success}/{total}, 실패 {fail_count}")
            
            self.refresh_tab_collected()


        def upload_to_naver():
            threading.Thread(target=upload_to_naver_thread, daemon=True).start()


        ttk.Button(header, text="네이버 상품등록", command=upload_to_naver).pack(side="left", padx=10)


        # ==========================================================
        # 🔹 Windly Thread (공용 라벨 사용)
        # ==========================================================
        def open_windly_thread():
            from automation.windly_uploader import WindlyUploader
            from automation.windly_config_loader import load_windly_config

            user_id, user_pw = load_windly_config()

            total = len(self.products_collected)
            if total == 0:
                messagebox.showwarning("알림", "윈들리에 입력할 상품이 없습니다.")
                return

            success = 0
            failed = []

            self.upload_status_label_global.config(text=f"윈들리 입력: 0/{total} 시작")

            for item in self.products_collected:

                uploader = WindlyUploader(user_id, user_pw)

                try:
                    ok = uploader.run_for_item(item)

                    # <<< 🔥 여기서 상태 업데이트
                    item.windly_status = "성공" if ok else "실패"
                    self.refresh_tab_collected()

                    if ok:
                        success += 1
                        self.upload_status_label_global.config(text=f"윈들리 입력: {success}/{total} 진행중")
                    else:
                        failed.append(item.final_name or item.url)
                        self.upload_status_label_global.config(
                            text=f"윈들리 입력: {success}/{total} 진행중 (실패 {len(failed)})"
                        )

                except Exception as e:
                    item.windly_status = "실패"
                    failed.append(item.final_name or item.url)
                    print("[WINDLY ERROR]", e)
                    self.upload_status_label_global.config(
                        text=f"윈들리 입력: {success}/{total} 진행중 (실패 {len(failed)})"
                    )

                time.sleep(0.4)

            fail_count = len(failed)
            messagebox.showinfo("윈들리 입력 완료", f"총 {total} 중 {success} 성공 / {fail_count} 실패")
            self.upload_status_label_global.config(text=f"윈들리 완료: {success}/{total}, 실패 {fail_count}")



        ttk.Button(header, text="윈들리 정보입력", command=lambda:
            threading.Thread(target=open_windly_thread, daemon=True).start()
        ).pack(side="left", padx=10)


        # 리스트 UI
        self.list_container = ttk.Frame(self.collected_frame)
        self.list_container.pack(fill="both", expand=True)
        self.refresh_tab_collected()

        
    def match_category_action(self, item):
        from category_matcher import CategoryMatcher

        # ⭐ UI 입력값을 직접 가져오기
        name = self.final_name_text.get("1.0", "end").strip()

        if not name:
            messagebox.showerror("오류", "최종 상품명이 입력되어 있지 않습니다.")
            return

        # 카테고리 매칭 실행
        result = CategoryMatcher.match(name)  # "50002801 | 패션의류 > 여성의류 > 바지"
        print("[GUI] 카테고리 매칭 결과:", result)

        # -------------------------------------------
        # 결과 파싱
        # -------------------------------------------
        try:
            code, category_path = result.split(" | ", 1)
        except:
            code = ""
            category_path = result

        # ProductItem에 반영
        item.category_code = code
        item.category_name = category_path

        # GUI 반영
        if code:
            new_text = f"카테고리: {category_path} ({code})"
        else:
            new_text = f"카테고리: {category_path}"

        self.category_result_label.config(text=new_text)


    # ==============================================================
    def update_tab_titles(self):
        self.nb.tab(0, text=f"상품수집 ({len(self.products_pending)})")
        self.nb.tab(1, text=f"수집완료 ({len(self.products_collected)})")

    # ==============================================================
    # 탭1 새로고침
    # ==============================================================
    def refresh_tab_pending(self):
    
        for w in self.pending_frame.winfo_children():
            w.destroy()

        for item in self.products_pending:

            row = ttk.Frame(self.pending_frame)
            row.pack(fill="x", pady=6)

            # ================= 왼쪽 텍스트 묶음 =================
            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            # URL (첫 줄)
            ttk.Label(text_frame, text=item.url, font=("맑은 고딕", 10, "bold")).pack(anchor="w")

            # 상태 (둘째 줄)
            status = "완료" if item in self.products_collected else "대기"
            clr = "green" if status == "완료" else "gray"

            ttk.Label(text_frame, text=f"수집: {status}", foreground=clr)\
                .pack(anchor="w", pady=(1,0))


            # ================= 오른쪽 : (시간 → 삭제 순) =================
            side = ttk.Frame(row)
            side.pack(side="right")

            # 🔥 시간 — 삭제 버튼 왼쪽
            ttk.Label(side, text=item.added_at, foreground="#666")\
                .pack(side="left", padx=(0,10))

            ttk.Button(side, text="삭제", command=lambda p=item: self.delete_pending(p))\
                .pack(side="left")


        self.update_tab_titles()


    # ==============================================================
    # 탭2 새로고침 (썸네일 캐싱 적용)
    # ==============================================================
    def refresh_tab_collected(self):
        
        for w in self.list_container.winfo_children():
            w.destroy()

        for item in self.products_collected:

            row = ttk.Frame(self.list_container)
            row.pack(fill="x", pady=7)

            # ================= 썸네일 =================
            thumb_label = ttk.Label(row, text="[로딩중]")
            thumb_label.pack(side="left", padx=5)

            if item.thumbnail_url:
                def cb(img, lbl=thumb_label):
                    if img:
                        lbl.configure(image=img, text=""); lbl.image = img
                    else:
                        lbl.configure(text="[이미지 오류]")
                load_image_async(item.thumbnail_url, (80,80), cb, self.root, disable_cache=True)
            else:
                thumb_label.configure(text="[이미지 없음]")

            # ================= 텍스트 =================
            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            name_txt = item.final_name or "(상품명 미정)"
            desc_txt = item.final_detail_text or "(상세설명 미정)"

            ttk.Label(text_frame, text=name_txt, font=("맑은 고딕", 10, "bold")).pack(anchor="w")

            short_desc = desc_txt.replace("\n", " ")
            if len(short_desc) > 40:
                short_desc = short_desc[:40] + "..."

            ttk.Label(text_frame, text=short_desc, foreground="#444").pack(anchor="w", fill="x")

            # ================= 🔥 상태별 색상 개별 적용 =================
            # item.naver_status / item.windly_status 값: "성공" / "실패" / "미등록"

            def color(v):
                return "green" if v=="성공" else ("red" if v=="실패" else "gray")

            n_status = getattr(item, "naver_status", "미등록")
            w_status = getattr(item, "windly_status", "미등록")

            status_row = ttk.Frame(text_frame)
            status_row.pack(anchor="w", pady=(3,0))

            ttk.Label(status_row, text=f"네이버: {n_status}", foreground=color(n_status)).pack(side="left", padx=(0,15))
            ttk.Label(status_row, text=f"윈들리: {w_status}", foreground=color(w_status)).pack(side="left")

            # ================= 버튼 =================
            ttk.Button(row, text="삭제",
                    command=lambda p=item: self.delete_collected(p)
                    ).pack(side="right", padx=5)

            ttk.Button(row, text="상세보기",
                    command=lambda p=item: self.open_detail(p)
                    ).pack(side="right", padx=5)

        self.update_tab_titles()


    
    # ==============================================================
    # 항목 추가
    # ==============================================================
    def add_product(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("알림", "URL을 입력해주세요.")
            return

        # ProductItem 생성
        item = ProductItem(url)

        # 추가된 날짜/시간 기록
        item.added_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # pending 리스트에 등록
        self.products_pending.append(item)

        # 입력창 비우기 + UI 갱신
        self.url_entry.delete(0, tk.END)
        self.refresh_tab_pending()



    # ==============================================================
    # 삭제(탭1)
    # ==============================================================
    def delete_pending(self, item):
        self.products_pending.remove(item)
        self.refresh_tab_pending()


    # ==============================================================
    # 삭제(탭2)
    # ==============================================================
    def delete_collected(self, item):
        self.products_collected.remove(item)
        self.refresh_tab_collected()
        
    def open_detail_description_preview(self, item):
    
        # --------------------------------------------------------------
        # 0) 영상 파일 생성 (미리보기용)
        # --------------------------------------------------------------
        if item.video_url:
            from utils.video_utils import download_and_convert_video

            mp4_path = download_and_convert_video(item.video_url)
            if mp4_path:
                item.video_file = mp4_path
            else:
                item.video_file = None
        else:
            item.video_file = None

        # --------------------------------------------------------------
        # 1) 상세 HTML 생성 (video_file 기반)
        # --------------------------------------------------------------
        html = generate_detail_html(item)

        # --------------------------------------------------------------
        # 2) temp HTML 파일 저장
        # --------------------------------------------------------------
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "detail_preview.html")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html)

        # --------------------------------------------------------------
        # 3) Chrome 경로 탐색
        # --------------------------------------------------------------
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            rf"C:\Users\{os.getlogin()}\AppData\Local\Google\Chrome\Application\chrome.exe"
        ]
        chrome_path = next((p for p in chrome_paths if os.path.exists(p)), "chrome")

        # --------------------------------------------------------------
        # 4) file:/// URL로 변환
        # --------------------------------------------------------------
        file_url = "file:///" + temp_path.replace("\\", "/")

        # --------------------------------------------------------------
        # 5) Chrome 팝업(app 모드) 실행
        # --------------------------------------------------------------
        try:
            subprocess.Popen([
                chrome_path,
                f'--app={file_url}',
                '--window-size=900,1600',
                '--disable-infobars',
                '--disable-extensions',
                '--force-device-scale-factor=1'
            ])
        except Exception as e:
            import tkinter as tk
            tk.messagebox.showerror("오류", f"Chrome 미리보기 실행 실패\n\n{e}")


    # =====================================================================
    # 상세보기 (즉시열림 + 4컬럼 + 캐싱 + 비동기 이미지 로딩 + 정렬/삭제)
    # =====================================================================
    def open_detail(self, item: ProductItem):
        print("\n========================")
        print("[DETAIL] 상세보기 클릭됨")
        print("========================")
        
        # ========== Toast UI 먼저 함수로 추가 ==========
        def toast(msg, parent, duration=2000):
            win = tk.Toplevel(parent)
            win.overrideredirect(True)
            win.attributes("-topmost", True)

            label = tk.Label(win, text=msg, bg="#333", fg="white",
                            font=("맑은 고딕", 11), padx=16, pady=8)
            label.pack()

            parent.update_idletasks()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()

            win.update_idletasks()
            ww = win.winfo_width()
            wh = win.winfo_height()

            win.geometry(f"{ww}x{wh}+{px+pw//2-ww//2}+{py+ph//2-wh//2}")
            win.after(duration, win.destroy)
        
        # 1) Toplevel 생성 직전
        print("[DETAIL] Toplevel 생성 시작")
        win = tk.Toplevel(self.root)
        self.detail_win = win
        self.detail_win.update() 
        
        print("[DETAIL] Toplevel 생성 완료")
        
        win.title("상품 상세정보")
        win.geometry("1600x900")
        win.configure(bg="#f7f7f7")
        print("[DETAIL] 창 기본속성 설정 완료")

        # ============================================================
        # 전체 레이아웃
        # ============================================================
        print("[DETAIL] 레이아웃 구성 시작")
        win.rowconfigure(0, weight=1)
        win.rowconfigure(1, weight=0, minsize=70)
        win.columnconfigure(0, weight=1)
        print("[DETAIL] 메인 content 영역 구성 완료")

        content = ttk.Frame(win)
        content.grid(row=0, column=0, sticky="nsew")

        # test_detail_window_expand.py 구조 적용
        content.columnconfigure(0, weight=1, uniform="col")
        content.columnconfigure(1, weight=1, uniform="col")
        content.columnconfigure(2, weight=1, uniform="col")
        content.columnconfigure(3, weight=1, uniform="col")
        content.columnconfigure(4, weight=1, uniform="col")
        content.rowconfigure(0, weight=1)
        print("[DETAIL] Grid 레이아웃 컬럼/로우 config 완료")
        
        
        # ============================================================
        # 1) 썸네일 패널
        # ============================================================
        thumb = ttk.LabelFrame(content, text="상품 썸네일", padding=10)
        thumb.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        thumb.grid_propagate(False)
        thumb.pack_propagate(False)

        # ============================================================
        # ① 템플릿 선택 UI(맨 위)
        # ============================================================
        dropdown_var = tk.StringVar(value="템플릿 선택 ▼")

        def open_dropdown():
            popup = tk.Toplevel(thumb)
            popup.title("썸네일 구성 방식 선택")
            popup.geometry("360x300")
            popup.grab_set()

            # ============= 이미지 유지용 캐시 추가 ============
            if not hasattr(self, "_tree_img_cache"):
                self._tree_img_cache = []   # 삭제되면 이미지도 사라짐!!!

            style = ttk.Style(popup)
            style.configure("Treeview", rowheight=60)

            tree = ttk.Treeview(popup, show="tree")
            tree.pack(fill="both", expand=True)

            import os
            from PIL import Image, ImageTk

            # ⭕ 캐시 저장 위치 변경
            def load_icon(filename):
                path = os.path.join("images", filename)
                if not os.path.exists(path):
                    print("NO ICON:", path)
                    return None
                try:
                    im  = Image.open(path).resize((60,60))
                    img = ImageTk.PhotoImage(im)
                    self._tree_img_cache.append(img)    # ★★ 유지 필수
                    return img
                except:
                    return None

            icon1 = load_icon("thumb01.jpg")
            icon2 = load_icon("thumb02.png")

            # 이미지 + 텍스트 표시 정상 작동
            tree.insert("", "end", text=" 상의 1명", image=icon1)
            tree.insert("", "end", text=" 하의 1명 + 제품 1개", image=icon2)

            def select(_):
                itemID = tree.focus()
                name = tree.item(itemID,"text").strip()
                dropdown_var.set(name+" ▼")
                popup.destroy()

            tree.bind("<<TreeviewSelect>>", select)

        ttk.Button(thumb, textvariable=dropdown_var,
                command=open_dropdown)\
                .pack(fill="x", padx=5, pady=(3,10))   # ← ⭐ thumb 최상단 위치 완료


        # ============================================================
        # ② 이미지 체크박스 목록 섹션 (아래로)
        # ============================================================
        from PIL import Image, ImageTk, ImageOps
        import urllib.request, io, threading

        # ==========================
        # 이미지 선택 저장 변수
        # ==========================
        self.selected_images = set()            # 선택 결과 저장
        self._grid_img_cache = []               # ※ GC방지 필수

        # ==========================
        # 옵션 > 메인 이미지 순서 정렬
        # ==========================
        all_option_imgs = []
        all_main_imgs = []

        for opt in item.parsed_raw.get("options", []):
            for v in opt.get("values", []):
                img = v.get("image")
                if isinstance(img, str) and img.startswith("http"):
                    all_option_imgs.append(img)

        for url in item.parsed_raw.get("images", []):
            if isinstance(url, str) and url.startswith("http"):
                all_main_imgs.append(url)

        all_imgs = all_option_imgs + all_main_imgs
        print(f"[DETAIL] 이미지 {len(all_imgs)}개")


        thumbnail_grid = ttk.Frame(thumb)  # 부모 = thumb
        thumbnail_grid.pack(fill="x", pady=(5,10))

        COLUMN = 4
        THUMB  = (60,60)
        self.selected_images = set()
        self._thumb_cache = []   # ※ GC 방지

        from PIL import ImageOps, Image, ImageTk
        import urllib.request, io, threading

        def async_thumb(url, label):
            def job():
                try:
                    raw = urllib.request.urlopen(url).read()
                    im = Image.open(io.BytesIO(raw))
                    im.thumbnail(THUMB)
                    im = ImageOps.pad(im, THUMB, color="white")

                    img = ImageTk.PhotoImage(im)
                    self._thumb_cache.append(img)        # ⭕ 유지 필수
                    label.after(1, lambda: label.config(image=img,text=""))
                except:
                    label.after(1, lambda: label.config(text="FAIL"))

            threading.Thread(target=job,daemon=True).start()


        # ---------- 이미지 체크박스 출력 ----------
        row = col = 0
        for url in all_imgs:
            cell = ttk.Frame(thumbnail_grid, padding=1)
            cell.grid(row=row, column=col, padx=2, pady=2, sticky="n")

            var = tk.BooleanVar()
            chk = ttk.Checkbutton(cell, variable=var)
            chk.pack(anchor="center")

            lb = ttk.Label(cell, text="loading...")
            lb.pack(anchor="center", pady=2)
            async_thumb(url, lb)

            # 🔥 클릭 토글 함수
            def toggle(u=url, v=var):
                if not v.get():  # 현재 OFF → ON
                    v.set(True)
                    self.selected_images.add(u)
                else:            # 현재 ON → OFF
                    v.set(False)
                    self.selected_images.discard(u)

            chk.config(command=toggle)
            lb.bind("<Button-1>", lambda e,u=url,v=var: toggle(u,v))   # ⭕ 이미지 클릭
            cell.bind("<Button-1>", lambda e,u=url,v=var: toggle(u,v)) # ⭕ 셀 전체 클릭

            col += 1
            if col == COLUMN:
                col = 0
                row += 1


        thumb.columnconfigure(0, weight=1)
        
        preview_label = ttk.Label(thumb, text="썸네일 미리보기 영역")
        preview_label.pack(anchor="center", pady=(10,5))
        
        def show_big_preview(path):
            from PIL import Image, ImageTk
            img = Image.open(path)
            img = img.resize((250,250))  # 원하는 크기로 조절 가능
            img = ImageTk.PhotoImage(img)

            preview_label.config(image=img)   # GUI 영역에 넣어서 사용
            preview_label.image = img         # 중요: GC 방지


        from image_tools.upper_focus import generate_upper_from_url   # 이미 제공한 파일 사용(상의 1명)

        # 🔥 GUI 공통 썸네일 결과 저장 위치 (템플릿 관계없음)
        THUMB_OUTPUT = "temp_img/final_thumbnail.png"

        def regen_thumbnail():
        
            template = dropdown_var.get().replace("▼","").strip()
            imgs = list(self.selected_images)

            from image_tools.upper_focus import generate_upper_from_url
            from image_tools.pp_focus import generate_thumbnail_from_urls, generate_thumbnail_from_paths

            THUMB_OUTPUT = "temp_img/final_thumbnail.png"
            os.makedirs("temp_img", exist_ok=True)

            # ============================================================
            # 템플릿 ① 상의 1명
            # ============================================================
            if template == "상의 1명" and len(imgs) == 1:
                ok, result = generate_upper_from_url(imgs[0])
                if ok:
                    os.replace(result, THUMB_OUTPUT)

            # ============================================================
            # 템플릿 ② 하의 + 제품
            # ============================================================
            elif template == "하의 1명 + 제품 1개" and len(imgs) == 2:
                ok, result = generate_thumbnail_from_urls(
                    imgs[0], imgs[1], output_path=THUMB_OUTPUT
                )

            # ❗ 예외 처리 → Toast + 종료
            else:
                print("⚠ 템플릿과 선택 이미지 수가 맞지 않습니다")
                toast("⚠ 템플릿과 선택 이미지 수가 맞지 않습니다", thumb)
                return

            # ============================================================
            # 최종 처리 — 하나의 파일로 생성되는 것 고정
            # ============================================================
            if ok:
                print(f"✔ 최종 썸네일 생성 → {THUMB_OUTPUT}")
                show_big_preview(THUMB_OUTPUT)  # GUI 미리보기 즉시 갱신
                toast("썸네일 생성 완료", thumb)  # ⭐ 성공 Toast
            else:
                print(f"❌ 생성 실패: {result}")
                toast("❌ 썸네일 생성 실패", thumb)



        ttk.Button(thumb, text="썸네일 생성", command=regen_thumbnail).pack(anchor="center", pady=(10,5))
        
        # ============================================================
        # 2) 이미지 패널
        # ============================================================
        print("[DETAIL] 상품 이미지 패널 생성 시작")
        left = ttk.LabelFrame(content, text="상품 이미지", padding=10)
        left.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        left.grid_propagate(False)
        left.pack_propagate(False)

        c1 = tk.Canvas(left)
        s1 = ttk.Scrollbar(left, orient="vertical", command=c1.yview)
        inner1 = ttk.Frame(c1)
        bind_mousewheel(inner1, c1)
        inner1_id = c1.create_window((0, 0), window=inner1, anchor="nw")
        c1.configure(yscrollcommand=s1.set)

        c1.pack(fill="both", expand=True, side="left")
        s1.pack(fill="y", side="right")
        print("[DETAIL] 이미지 목록 패널 UI 구성 완료")

        def on_resize_c1(e):
            c1.itemconfig(inner1_id, width=e.width)

        c1.bind("<Configure>", on_resize_c1)
        inner1.bind("<Configure>", lambda e: c1.configure(scrollregion=c1.bbox("all")))

        images = item.parsed_raw.get("images", [])
        print(f"[DETAIL] 이미지 목록 로드 완료 (총 {len(images)}개)")

        def refresh_images():
            print("[DETAIL] refresh_images() 실행됨")
            print(f"[DETAIL] 기존 위젯 삭제 시작 ({len(inner1.winfo_children())}개)")
            for w in inner1.winfo_children():
                w.destroy()

            print("[DETAIL] 이미지 위젯 재생성 시작")
            for idx, url in enumerate(images):
                print(f"[DETAIL] 이미지 row 생성 idx={idx} url={url[:60]}")
                row = ttk.Frame(inner1, padding=5)
                row.pack(fill="x", pady=5)

                lbl = ttk.Label(row, text="로딩중...")
                lbl.pack(side="left", padx=4)

                print(f"[ASYNC-REQ] 이미지 비동기 요청됨 idx={idx}")
                load_image_async(
                    url, (140, 140),
                    lambda img, lbl=lbl: (
                        print(f"[ASYNC-CB] 콜백 실행 url={url[:60]}, 성공={img is not None}"),
                        lbl.configure(image=img, text="") if img else lbl.configure(text="[오류]"),
                        setattr(lbl, "image", img)
                    ), self.root
                )

                ttk.Button(row, text="삭제", width=7,
                        command=lambda i=idx: delete_img(i)).pack(side="right")
                ttk.Button(row, text="▲", width=3,
                        command=lambda i=idx: move_up(i)).pack(side="right")
                ttk.Button(row, text="▼", width=3,
                        command=lambda i=idx: move_down(i)).pack(side="right")
                

        def move_up(i):
            if i > 0:
                images[i], images[i - 1] = images[i - 1], images[i]
                item.thumbnail_url = images[0] if images else None
                refresh_images()

        def move_down(i):
            if i < len(images) - 1:
                images[i], images[i + 1] = images[i + 1], images[i]
                item.thumbnail_url = images[0] if images else None
                refresh_images()

        def delete_img(i):
            del images[i]
            item.thumbnail_url = images[0] if images else None
            refresh_images()

        refresh_images()
        print("[DETAIL] 이미지 목록 refresh_images() 호출 완료")

        # ============================================================
        # 2) 상품명 패널 전체 (스크롤 내부에 모두 포함)
        # ============================================================
        mid = ttk.LabelFrame(content, text="상품명", padding=10)
        mid.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # ──────────────────────────────
        # Canvas(스크롤) 생성
        # ──────────────────────────────
        c2 = tk.Canvas(mid)
        s2 = ttk.Scrollbar(mid, orient="vertical", command=c2.yview)
        inner2 = ttk.Frame(c2)

        bind_mousewheel(inner2, c2)

        inner2_id = c2.create_window((0,0), window=inner2, anchor="nw")
        c2.configure(yscrollcommand=s2.set)

        c2.pack(fill="both", expand=True, side="left")
        s2.pack(fill="y", side="right")

        c2.bind("<Configure>", lambda e: c2.itemconfig(inner2_id, width=e.width))
        inner2.bind("<Configure>", lambda e: c2.configure(scrollregion=c2.bbox("all")))

        # ──────────────────────────────
        # (A) 이미지 리스트 (가장 최상단)
        # ──────────────────────────────
        from PIL import Image, ImageTk
        import urllib.request, io, threading

        self.selected_main_image = tk.StringVar()
        self._grid_img_cache = []

        all_option_imgs = []
        all_main_imgs = []

        # 옵션 이미지 우선
        for opt in item.parsed_raw.get("options", []):
            for v in opt.get("values", []):
                img = v.get("image")
                if isinstance(img, str) and img.startswith("http"):
                    all_option_imgs.append(img)

        # 상품 메인 이미지
        for url in item.parsed_raw.get("images", []):
            if isinstance(url, str) and url.startswith("http"):
                all_main_imgs.append(url)

        # 옵션 → 메인 순서
        all_imgs = all_option_imgs + all_main_imgs
        print(f"[DETAIL] 이미지 {len(all_imgs)}개")

        # 그리드 UI
        COLUMN = 4
        THUMB = (60, 60)

        from PIL import ImageOps   # ← 추가 필요

        def async_load(url, label):
            def job():
                try:
                    raw = urllib.request.urlopen(url, timeout=5).read()
                    im = Image.open(io.BytesIO(raw))

                    # ⭐ 이미지 크기 통일 (비율무관 60x60 정사각형으로 균등 정렬)
                    im.thumbnail(THUMB)
                    im = ImageOps.pad(im, THUMB, color="white")  # ← 패딩으로 사이즈 완전 통일

                    photo = ImageTk.PhotoImage(im)
                    self._grid_img_cache.append(photo)
                    label.after(1, lambda: label.config(image=photo, text=""))
                except:
                    label.after(1, lambda: label.config(text="LOAD_FAIL"))
            threading.Thread(target=job, daemon=True).start()

        def toggle_radio(v):
            cur = self.selected_main_image.get()
            self.selected_main_image.set("" if cur == v else v)

        row = col = 0
        for url in all_imgs:
            cell = ttk.Frame(inner2, padding=0)

            # 🔥 좌/우/상/하 공간 없이 정렬 + 높이 균일하게
            cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

            rb = ttk.Radiobutton(cell, variable=self.selected_main_image, value=url)
            rb.pack(anchor="center")

            lb = ttk.Label(cell, text="loading...")
            lb.pack()

            rb.bind("<Button-1>", lambda e, u=url: toggle_radio(u))
            lb.bind("<Button-1>", lambda e, u=url: toggle_radio(u))
            cell.bind("<Button-1>", lambda e, u=url: toggle_radio(u))

            async_load(url, lb)

            col += 1
            if col == COLUMN:
                col = 0
                row += 1

        img_end_row = row
        inner2.columnconfigure(0, weight=1)

        row = img_end_row + 1


        # ============================================================
        # (A) ← 키워드 먼저 배치
        # ============================================================
        keyword_frame = ttk.Frame(inner2, padding=5)
        keyword_frame.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(0,10))

        self.keyword_textbox = tk.Text(keyword_frame, height=6, wrap="word")
        self.keyword_textbox.pack(fill="x")

        keywords = item.name_keywords if getattr(item,"name_keywords",None) else []
        if keywords:
            self.keyword_textbox.insert("1.0", ", ".join(keywords))

        from pname_keyword import extract_keywords
        def refresh_keywords():
            current_name = self.final_name_text.get("1.0","end").strip()
            if not current_name:
                print("[KEYWORD] 상품명 없음 → 수집 불가")
                return

            new_keywords = extract_keywords(current_name)
            item.name_keywords = new_keywords
            self.keyword_textbox.delete("1.0","end")
            self.keyword_textbox.insert("1.0", ", ".join(new_keywords))
            print("[KEYWORD UPDATED]", new_keywords)

        ttk.Button(keyword_frame, text="키워드 수집", command=refresh_keywords).pack(anchor="w", pady=(6,0))


        row += 2   # ← 다음 섹션 위치 확보

        orig_name = getattr(item, "original_name", "(원본 없음)")
        orig_label = tk.Text(inner2, height=2, wrap="word", bg="#eee")
        orig_label.insert("1.0", orig_name)
        orig_label.config(state="disabled")
        orig_label.grid(row=row, column=0, columnspan=4, sticky="ew", padx=5, pady=(5,10))

        row += 2

        ttk.Label(inner2, text="■ 최종 상품명").grid(row=row, column=0, columnspan=4, sticky="w", pady=(10,0))
        row += 1
        
        name_frame = ttk.Frame(inner2, padding=10)
        name_frame.grid(row=row, column=0, columnspan=4, sticky="ew")

        self.final_name_text = tk.Text(name_frame, height=2, wrap="word")
        self.final_name_text.pack(fill="x")


        # ───────── 상품명 생성 함수 ─────────
        from utils.product_name_generator import generate_final_name

        def generate_product_name_action(item):
            translated_name = item.original_name or item.parsed_raw.get("original_name") or ""

            # 🔥 UI 키워드 입력폼에서 직접 키워드 수집하도록 변경
            raw_keywords = self.keyword_textbox.get("1.0", "end").strip()
            keywords = [kw.strip() for kw in raw_keywords.replace("\n"," ").split(",") if kw.strip()]

            if not translated_name:
                print("[ERROR] 원본상품명 없음")
                return
            if not keywords:
                print("[ERROR] 키워드 없음 → UI 키워드 입력이 비어 있음")
                return

            selected_img = self.selected_main_image.get() or None
            print(f"[IMG SELECT] {selected_img}")

            new_name = generate_final_name(
                translated_name = translated_name,
                keyword_list    = keywords,    # ← 이제 UI 입력 키워드 기반
                image_url       = selected_img
            )

            if new_name:
                item.final_name = new_name
                self.final_name_text.delete("1.0","end")
                self.final_name_text.insert("1.0",new_name)
                print(f"[FINAL NAME] {new_name}")
            else:
                print("[상품명 실패] 결과 없음")


        ttk.Button(name_frame, text="상품명 생성", command=lambda p=item: generate_product_name_action(p)).pack(anchor="w", pady=5)

        # 기존 final_name 있으면 미리 적용
        initial = item.final_name or ""
        self.final_name_text.insert("1.0", initial)
        
        row += 3   # ← 최종상품명 아래를 다시 확보

        # ============================================================
        # (D) 카테고리 영역
        # ============================================================
        ttk.Label(inner2, text="■ 카테고리").grid(row=row+4, column=0, columnspan=4, sticky="w", pady=(10,0))
        
        category_section = ttk.Frame(inner2, padding=10)
        category_section.grid(row=row+5, column=0, columnspan=4, sticky="ew", pady=(0,10))

        txt = "카테고리: 아직 선택되지 않음"
        if getattr(item,"category_name",None):
            if getattr(item,"category_code",None):
                txt = f"카테고리: {item.category_name} ({item.category_code})"
            else:
                txt = f"카테고리: {item.category_name}"

        self.category_result_label = ttk.Label(category_section, text=txt, foreground="#333")
        self.category_result_label.pack(anchor="w", pady=(0,5))

        ttk.Button(category_section,text="카테고리 매칭",command=lambda p=item:self.match_category_action(p)).pack(anchor="w")

        # 최종 스크롤 갱신
        inner2.update_idletasks()
        c2.configure(scrollregion=c2.bbox("all"))



        # ============================================================
        # 3) 옵션 패널 (수정 가능 Entry 버전)
        # ============================================================
        opt = ttk.LabelFrame(content, text="옵션", padding=10)
        opt.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)
        
        opt.grid_propagate(False)
        opt.pack_propagate(False)

        c3 = tk.Canvas(opt)
        s3 = ttk.Scrollbar(opt, orient="vertical", command=c3.yview)
        inner3 = ttk.Frame(c3)
        bind_mousewheel(inner3, c3)
        inner3_id = c3.create_window((0, 0), window=inner3, anchor="nw")
        c3.configure(yscrollcommand=s3.set)

        c3.pack(fill="both", expand=True, side="left")
        s3.pack(fill="y", side="right")

        def on_resize_c3(e):
            c3.itemconfig(inner3_id, width=e.width)

        c3.bind("<Configure>", on_resize_c3)
        inner3.bind("<Configure>", lambda e: c3.configure(scrollregion=c3.bbox("all")))

        parsed = item.parsed_raw
        options = parsed.get("options", [])

        # 저장용: Entry 객체 저장할 딕셔너리
        entry_map = {}   # (group_index, value_index) → Entry

        if not options:
            ttk.Label(inner3, text="옵션 없음").pack(anchor="w", pady=10)
        else:
            for gi, group in enumerate(options):
                ttk.Label(inner3, text=f"■ {group['group_name']}").pack(anchor="w", pady=(10, 4))

                for vi, v in enumerate(group["values"]):
                    row = ttk.Frame(inner3)
                    row.pack(anchor="w", pady=4)

                    # 이미지 있으면 로드
                    if v.get("image"):
                        lbl = ttk.Label(row, text="로딩중...")
                        lbl.pack(side="left")

                        load_image_async(
                            v["image"], (40, 40),
                            lambda img, lbl=lbl: (
                                lbl.configure(image=img, text="") if img else lbl.configure(text="[오류]"),
                                setattr(lbl, "image", img),
                            ), 
                            self.root
                        )

                    # ENTRY 위젯 생성 (옵션값 name 수정 가능)
                    e = ttk.Entry(row, width=25)
                    e.insert(0, v["name"])
                    e.pack(side="left", padx=6)

                    # Entry 등록
                    entry_map[(gi, vi)] = e
                    
        # ============================================================
        # 가격 정보 (옵션과 별개)
        # ============================================================
        ttk.Label(inner3, text="\n■ 가격 목록").pack(anchor="w", pady=4)
        for cd, price in parsed.get("prices", {}).items():
            ttk.Label(inner3, text=f"{cd}: {price}", wraplength=240).pack(anchor="w")
                    
        # -------------------------------
        # 가격 정보 표시 (옵션 패널 상단)
        # -------------------------------
        price_frame = ttk.Frame(inner3)
        price_frame.pack(fill="x", pady=(5, 10))

        raw_price = getattr(item, "base_price", None)
        currency = getattr(item, "price_currency", None)
        price_krw = getattr(item, "base_price_krw", None)

        raw_txt = raw_price if raw_price else "가격 정보 없음"
        cur_txt = f"({currency})" if currency else ""
        krw_txt = f"{price_krw:,}원" if price_krw else "-"

        ttk.Label(price_frame, text=f"대표 가격: {raw_txt} {cur_txt}").pack(anchor="w")
        ttk.Label(price_frame, text=f"원화 환산: {krw_txt}", foreground="#444").pack(anchor="w", pady=(2,0))

        # ============================================================
        # 저장 버튼 (Entry 값 → parsed_raw 반영)
        # ============================================================
        def save_option_changes():
            print("[옵션 저장] Entry 값 → parsed_raw 적용 시작")

            for gi, group in enumerate(options):
                for vi, v in enumerate(group["values"]):
                    new_val = entry_map[(gi, vi)].get().strip()
                    print(f"[UPDATE] {group['group_name']}  {v['name']} → {new_val}")
                    v["name"] = new_val  # 값 업데이트

            # parsed_raw 업데이트
            item.parsed_raw["options"] = options
            
            from utils.detail_description_generator import (
                render_options_section,
                html_to_png_options,
            )
            
            # ----- 옵션 PNG 다시 생성 -----
            options_html = render_options_section(item.parsed_raw.get("options", []))
            item.options_chart_path = html_to_png_options(options_html)
            
            print("[옵션 저장 완료]")


        btn = ttk.Button(inner3, text="옵션 변경사항 저장", command=save_option_changes)
        btn.pack(anchor="w", pady=10)

        # ============================================================
        # 4) 상세설명 패널
        # ============================================================
        detail = ttk.LabelFrame(content, text="상세설명", padding=10)
        detail.grid(row=0, column=4, sticky="nsew", padx=5, pady=5)
        
        detail.grid_propagate(False)
        detail.pack_propagate(False)

        c4 = tk.Canvas(detail)
        s4 = ttk.Scrollbar(detail, orient="vertical", command=c4.yview)
        inner4 = ttk.Frame(c4)
        bind_mousewheel(inner4, c4)
        inner4_id = c4.create_window((0, 0), window=inner4, anchor="nw")
        c4.configure(yscrollcommand=s4.set)

        c4.pack(fill="both", expand=True, side="left")
        s4.pack(fill="y", side="right")

        def on_resize_c4(e):
            c4.itemconfig(inner4_id, width=e.width)

        c4.bind("<Configure>", on_resize_c4)
        inner4.bind("<Configure>", lambda e: c4.configure(scrollregion=c4.bbox("all")))

        # ===========================================
        # ✔ 상세설명 수정 가능한 Text 입력폼으로 변경
        # ===========================================
        detail_text = item.final_detail_text or item.detail_text or ""

        text_box = tk.Text(
            inner4,
            wrap="word",
            height=27,
            font=("맑은 고딕", 10)
        )
        text_box.pack(fill="both", padx=5, pady=10)

        # ▶ 텍스트 삽입
        text_box.insert("1.0", detail_text)
        
        from llm.llm_detail_generator import generate_sections_from_llm
        from utils.html_cleaner import html_to_text, format_description_blocks

        def _regen_desc_event():
            original_text = item.detail_text or ""

            if not original_text.strip():
                messagebox.showwarning("알림", "원본 상세설명이 없습니다.", parent=win)
                return

            try:

                # LLM 호출 → HTML 생성
                llm_html = generate_sections_from_llm(original_text)

                # HTML → TEXT
                text_raw = html_to_text(llm_html)
                final_text = format_description_blocks(text_raw)

                # 텍스트박스 갱신
                text_box.delete("1.0", "end")
                text_box.insert("1.0", final_text)

                # 내부 저장
                item.final_detail_text = final_text
                item.final_detail_html = llm_html

            except Exception as e:
                messagebox.showerror("오류", f"상세설명 생성 중 오류: {e}", parent=win)
                print("[ERROR] regenerate_desc:", e)

        btn_frame = ttk.Frame(inner4)
        btn_frame.pack(pady=10, fill="x")
        
        # 버튼 생성
        ttk.Button(btn_frame, text="상세설명 생성", command=_regen_desc_event).pack(side="left", padx=5)

        
        # ============================================================
        # 상세설명 저장 버튼
        # ============================================================
        def save_description():
            new_text = text_box.get("1.0", "end").strip()
            item.final_detail_text = new_text

            # 🔥 저장할 때 HTML로 변환하여 final_detail_html도 업데이트
            from utils.html_cleaner import text_to_html
            item.final_detail_html = text_to_html(new_text)

            messagebox.showinfo("저장됨", "상세설명이 저장되었습니다.", parent=win)


        ttk.Button(btn_frame, text="상세설명 저장", command=save_description).pack(side="left", padx=5)


        # ============================================================
        # 상세설명 HTML 미리보기 버튼 추가
        # ============================================================
        ttk.Button(
            btn_frame,
            text="미리보기",
            command=lambda p=item: self.open_detail_description_preview(p)
        ).pack(side="left", padx=5)
        
        SIZE_MAPPING_PATH = os.path.join("templates", "size_header_mapping.json")

        # --- 매핑 파일 읽기 ---
        def load_size_mapping():
            if not os.path.exists(SIZE_MAPPING_PATH):
                return {}
            try:
                with open(SIZE_MAPPING_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}

        # -----------------------------------------
        # UI 제목
        # -----------------------------------------
        ttk.Label(inner4, text="■ 사이즈 헤더").pack(anchor="w", pady=(20, 5))

        # -----------------------------------------
        # 원본 헤더 가져오기 (파서 제공값 사용)
        # -----------------------------------------
        original_headers = item.size_headers_original or []

        # 중복 제거
        original_headers = list(dict.fromkeys(original_headers))

        # 매핑 파일 로딩
        current_mapping = load_size_mapping()

        from utils.detail_description_generator import translate_header

        # 스타일 등록 (번역 fallback용)
        style = ttk.Style()
        style.configure("Translated.TEntry", foreground="#777")   # 번역 fallback = 회색
        style.configure("Mapped.TEntry", foreground="#000")        # 매핑됨 = 검정

        ...

        # -----------------------------------------
        # 매핑 입력 UI (왼쪽: 원문 Entry / 오른쪽: 매핑 후 Entry)
        # -----------------------------------------
        map_frame = ttk.Frame(inner4)
        map_frame.pack(fill="x", pady=10)

        left_entries = []
        right_entries = []

        for h in original_headers:
            row = ttk.Frame(map_frame)
            row.pack(fill="x", pady=2)

            row.columnconfigure(0, weight=1)   # ← 왼쪽 Entry 50%
            row.columnconfigure(1, weight=1)   # ← 오른쪽 Entry 50%

            # 왼쪽 Entry
            e_left = ttk.Entry(row)
            e_left.insert(0, h)
            e_left.grid(row=0, column=0, padx=5, sticky="ew")
            left_entries.append(e_left)

            # 오른쪽 Entry
            mapped = current_mapping.get(h)
            if mapped:
                display_val = mapped
                entry_style = "Mapped.TEntry"
            else:
                display_val = translate_header(h)
                entry_style = "Translated.TEntry"

            e_right = ttk.Entry(row, style=entry_style)
            e_right.insert(0, display_val)
            e_right.grid(row=0, column=1, padx=5, sticky="ew")
            right_entries.append(e_right)


        # -----------------------------------------
        # JSON 파일 직접 수정 버튼
        # -----------------------------------------
        def open_header_json_editor():
            top = tk.Toplevel(win)
            top.title("size_header_mapping.json 편집")
            top.geometry("700x650")

            txt = tk.Text(top, wrap="none")
            txt.pack(expand=True, fill="both")

            # 파일 읽기
            if os.path.exists(SIZE_MAPPING_PATH):
                with open(SIZE_MAPPING_PATH, "r", encoding="utf-8") as f:
                    txt.insert("1.0", f.read())
            else:
                txt.insert("1.0", "{}")

            # 저장 버튼
            def save_json():
                try:
                    raw = txt.get("1.0", "end")
                    json.loads(raw)  # JSON 형식 검증

                    # JSON 새로 저장
                    with open(SIZE_MAPPING_PATH, "w", encoding="utf-8") as f:
                        f.write(raw)

                    # --- 모듈 리로드 ---
                    import importlib
                    import utils.detail_description_generator as ddg
                    importlib.reload(ddg)

                    # --- 번역 캐시 초기화 ---
                    ddg.HEADER_TRANSLATE_CACHE.clear()

                    # --- 최신 매핑으로 사이즈표 HTML 재생성 ---
                    item.size_html = ddg.normalize_size_chart(
                        item.size_headers_original,
                        item.size_rows_original
                    )

                    # --- PNG 재생성 ---
                    if item.size_html and item.size_html.strip():
                        item.size_chart_image_path = ddg.html_to_png_final(
                            item.size_html,
                            output_name=f"{item.item_id}_size.png"
                        )
                    else:
                        item.size_chart_image_path = None

                    # ------------------------------------------------------
                    # 🔥 UI 오른쪽 Entry 값 실시간 갱신
                    # ------------------------------------------------------
                    # JSON 다시 로드
                    new_mapping = json.loads(raw)

                    # 오른쪽 Entry 리스트 업데이트
                    for left_entry, right_entry in zip(left_entries, right_entries):
                        original_key = left_entry.get().strip()

                        mapped_value = new_mapping.get(original_key, "")

                        # 기존 내용 삭제 후 새 값 삽입
                        right_entry.delete(0, "end")
                        right_entry.insert(0, mapped_value)

                    messagebox.showinfo("저장됨", "size_header_mapping.json 저장되었습니다.", parent=top)
                    
                    top.destroy()

                except Exception as e:
                    messagebox.showerror("오류", f"JSON 형식 오류: {e}", parent=top)


            ttk.Button(top, text="저장", command=save_json).pack(pady=5)
            
        # -----------------------------------------
        # 버튼 2개를 가로 일렬 배치
        # -----------------------------------------
        btn_row = ttk.Frame(inner4)
        btn_row.pack(pady=10)
        
        ttk.Button(btn_row, text="헤더 매핑 파일 열기", command=open_header_json_editor).pack(side="left", padx=5)
        
        # -----------------------------------------
        # 영상 파일 제목
        # -----------------------------------------
        ttk.Label(inner4, text="■ 영상 파일").pack(anchor="w", pady=(20, 5))
        
        # ====== 사이즈 헤더 아래에 추가 ======

        if item.video_url:
            ttk.Label(inner4, text="영상 있음", foreground="#333").pack(anchor="w")
        else:
            ttk.Label(inner4, text="영상 없음", foreground="#999").pack(anchor="w")

        def open_formatter_editor():
            
            editor = tk.Toplevel(self.root)
            editor.title("LLM Formatter 편집기")
            editor.geometry("900x700")

            # 파일 경로
            formatter_path = "llm/llm_formatter.py"

            # Text 위젯
            text = tk.Text(editor, wrap="none")
            text.pack(fill="both", expand=True)

            # 파일 읽기
            with open(formatter_path, "r", encoding="utf-8") as f:
                text.insert("1.0", f.read())

            # 저장 버튼
            def save_changes():
                new_code = text.get("1.0", "end-1c")
                with open(formatter_path, "w", encoding="utf-8") as f:
                    f.write(new_code)

                import importlib
                import llm.llm_client
                llm.llm_client.reload_formatter()
                importlib.reload(llm.llm_client)


                print("[FORMATTER] llm_formatter.py 저장됨 + reload 완료!")

                messagebox.showinfo("저장 완료", "llm_formatter.py 파일이 저장되었고 즉시 반영되었습니다.", parent=win)
                
                editor.destroy()

            ttk.Button(editor, text="저장", command=save_changes).pack(pady=5)


        # ============================================================
        # 저장 버튼
        # ============================================================
        def save_all():
            # 상품명 저장
            item.final_name = self.final_name_text.get("1.0", "end").strip()
            
            # NEW: UI 키워드 저장 추가
            raw_kw = self.keyword_textbox.get("1.0", "end").strip()       # ← UI에 있는 키워드 Textbox
            kw_list = [k.strip() for k in raw_kw.replace("\n"," ").split(",") if k.strip()]
            item.name_keywords = kw_list   
    
            # -----------------------------------
            # ① UI 입력 텍스트 저장
            # -----------------------------------
            cleaned_text = text_box.get("1.0", "end").strip()
            item.final_detail_text = cleaned_text

            # -----------------------------------
            # ② 텍스트 → HTML 변환하여 final_detail_html 생성
            # -----------------------------------
            from utils.html_cleaner import text_to_html
            item.final_detail_html = text_to_html(cleaned_text)

            # -----------------------------------
            # ③ 이미지/렌즈 데이터 업데이트
            # -----------------------------------
            item.parsed_raw["images"] = images
            
            # -----------------------------------
            # ④ 창 닫기 & 탭 새로고침
            # -----------------------------------
            win.destroy()
            self.refresh_tab_collected()
            
        bottom_frame = ttk.Frame(win)
        bottom_frame.grid(row=1, column=0, pady=20)
        ttk.Button(bottom_frame, text="저장/닫기", command=save_all).pack(side="right", padx=5)
        ttk.Button(bottom_frame, text="프롬프트", command=open_formatter_editor).pack(side="right", padx=5)


            
    # =================================================================
    # 정보 수집 전체 실행 — 수집대기 상품은 삭제하지 않음
    # =================================================================
    def collect_all(self):
    
        if not self.products_pending:
            messagebox.showinfo("알림", "수집할 상품이 없습니다.")
            return

        # 📌 공용 상태표시 라벨 (없으면 생성)
        if not hasattr(self, "upload_status_label_global"):
            self.upload_status_label_global = ttk.Label(self.root, text="대기중", foreground="blue")
            self.upload_status_label_global.pack(anchor="ne", pady=2, padx=8)

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
                        self.upload_status_label_global.config(text=f"수집 {idx}/{total} (실패 {len(failed)})")
                        continue

                    item.load_data(result)

                    if not any(c.url == item.url for c in self.products_collected):
                        self.products_collected.append(item)

                    success += 1
                    self.upload_status_label_global.config(text=f"수집 {success}/{total} 진행중")

                except Exception as e:
                    failed.append(item.url)
                    print("[COLLECT ERROR]", item.url, e)
                    self.upload_status_label_global.config(text=f"수집 {success}/{total} (실패 {len(failed)})")

                self.refresh_tab_pending()
                self.refresh_tab_collected()
                self.root.update_idletasks()
                time.sleep(0.2)

            fail_count = len(failed)
            msg = f"총 {total}개 중 {success} 성공\n실패 {fail_count}개"

            if fail_count > 0:
                msg += "\n\n실패 목록:\n" + "\n".join(" • "+u for u in failed)

            messagebox.showinfo("수집 완료", msg)

            self.upload_status_label_global.config(
                text=f"수집 완료 {success}/{total} 실패 {fail_count}"
            )

        threading.Thread(target=task, daemon=True).start()




    # =================================================================
    def on_close(self):
        try:
            requests.post("http://127.0.0.1:5001/shutdown", timeout=1)
        except:
            pass
        self.root.destroy()



# =================================================================
# 실행
# =================================================================
def run_gui():
    root = tk.Tk()
    root.geometry("1400x800")
    app = ProductCollectorGUI(root)
    root.mainloop()