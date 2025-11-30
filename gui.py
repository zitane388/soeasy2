# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk
import io, os, tempfile, subprocess
import threading, time, json
import base64
from websocket import create_connection
from datetime import datetime

from models import ProductItem
from scraper import Scraper
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
        self.scraper = Scraper()

        # 데이터 저장
        self.products_pending = []        # 탭1 (수집대기)
        self.products_collected = []      # 탭2 (수집완료)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_ui()


    # ==============================================================
    # UI 구성
    # ==============================================================
    def build_ui(self):
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.nb = ttk.Notebook(self.root)
        self.nb.grid(row=0, column=0, sticky="nsew")

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

        # -------------------------
        # 상단 헤더 (버튼 영역)
        # -------------------------
        header = ttk.Frame(self.collected_frame)
        header.pack(fill="x", pady=5)

        def upload_to_naver():
            from naver_uploader import NaverUploader
            uploader = NaverUploader()
            uploader.run(self.products_collected)

        ttk.Button(
            header,
            text="네이버 상품등록",
            command=upload_to_naver
        ).pack(side="left", padx=10)
        
        def open_windly_thread():
            from automation.windly_uploader import WindlyUploader
            from automation.windly_config_loader import load_windly_config

            # 1) Windly 설정 파일 로딩
            user_id, user_pw = load_windly_config()

            # 2) Uploader 생성
            uploader = WindlyUploader(
                user_id=user_id,
                user_pw=user_pw
            )

            print("[Windly] 브라우저 준비 중...")
            uploader.prepare()

            # 3) 전체 상품 반복 처리
            for item in self.products_collected:
                print(f"[Windly] 처리 중 → {item.final_name}")
                uploader.run_for_item(item)

            print("[Windly] 모든 상품 Windly 상세페이지 열기 완료")


        def open_windly():
            import threading
            threading.Thread(target=open_windly_thread, daemon=True).start()


        ttk.Button(
            header, 
            text="윈들리 정보입력",
            command=open_windly
        ).pack(side="left", padx=10)


        # -------------------------
        # 리스트 컨테이너 (여기만 refresh)
        # -------------------------
        self.list_container = ttk.Frame(self.collected_frame)
        self.list_container.pack(fill="both", expand=True)

        self.refresh_tab_collected()
        
    def match_category_action(self, item):
        from category_matcher import CategoryMatcher
        name = item.final_name
        if not name:
            messagebox.showerror("오류", "먼저 상품명을 생성하세요.")
            return
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

        # ProductItem에 저장
        item.category_code = code
        item.category_name = category_path
        
        if code:
            new_text = f"카테고리: {category_path} ({code})"
        else:
            new_text = f"카테고리: {category_path}"

        # GUI 라벨 업데이트
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
            row.pack(fill="x", pady=4)

            # ─────────────────────────────────────
            # 1) URL (왼쪽 정렬)
            # ─────────────────────────────────────
            url_label = ttk.Label(row, text=item.url)
            url_label.grid(row=0, column=0, sticky="w", padx=(0, 10))

            # ─────────────────────────────────────
            # 2) 추가한 날짜·시간 (오른쪽)
            # ─────────────────────────────────────
            time_label = ttk.Label(row, text=item.added_at)
            time_label.grid(row=0, column=1, sticky="e", padx=(0, 6))

            # ─────────────────────────────────────
            # 3) 삭제 버튼 (오른쪽, 시간 오른쪽에 딱 붙음)
            # ─────────────────────────────────────
            delete_btn = ttk.Button(
                row, text="삭제",
                command=lambda p=item: self.delete_pending(p)
            )
            delete_btn.grid(row=0, column=2, sticky="e")

            # 🔥 오른쪽 정렬을 제대로 유지하려면 col1·col2에 weight를 줘야 함
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)
            row.grid_columnconfigure(2, weight=0)
            
        self.update_tab_titles()

    # ==============================================================
    # 탭2 새로고침 (썸네일 캐싱 적용)
    # ==============================================================
    def refresh_tab_collected(self):
    
        # header는 냅두고, list_container만 깔끔히 초기화
        for w in self.list_container.winfo_children():
            w.destroy()

        # 상품 리스트 구성
        for item in self.products_collected:

            row = ttk.Frame(self.list_container)
            row.pack(fill="x", pady=7)

            # 썸네일
            thumb_label = ttk.Label(row, text="[로딩중]")
            thumb_label.pack(side="left", padx=5)

            if item.thumbnail_url:
                def cb(img, lbl=thumb_label):
                    if img:
                        lbl.configure(image=img, text="")
                        lbl.image = img
                    else:
                        lbl.configure(text="[이미지 오류]")

                load_image_async(item.thumbnail_url, (80,80), cb, self.root, disable_cache=True)
            else:
                thumb_label.configure(text="[이미지 없음]")

            # 텍스트 영역
            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            name_txt = item.final_name if item.final_name else "(상품명 미정)"
            desc_txt = item.final_detail_text if item.final_detail_text else "(상세설명 미정)"

            ttk.Label(text_frame, text=name_txt).pack(anchor="w")
            ttk.Label(text_frame, text=desc_txt[:80] + "...").pack(anchor="w")
            
            ttk.Button(row, text="삭제",
                    command=lambda p=item: self.delete_collected(p)
                    ).pack(side="right", padx=5)
            
            # 상세보기 버튼을 나중에
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



    def generate_product_name_action(self, item):
        try:
            raw_p_keywords = []
            for p in item.lens_products:
                name = p.get("name")
                if name:
                    raw_p_keywords.append(name)

            # 단어 단위로 분해 + 불필요한 문자 제거
            p_keywords = []
            for text in raw_p_keywords:
                # 개행 제거 + split
                words = text.replace("\n", " ").split()
                for w in words:
                    # 특수문자 제거
                    w = w.strip().strip(".,()[]“”\"'")
                    # 너무 짧은 단어 제거 (예: ‘에’, ‘이’, ‘및’ 등)
                    if len(w) <= 1:
                        continue
                    p_keywords.append(w)
            
            p_keywords = list(dict.fromkeys(p_keywords))

            # 2) 2차 키워드 생성 (상세설명 기반)
            desc = item.final_detail_text or item.parsed_raw.get("detail_text") or ""
            s_keywords = desc.replace("\n", " ").split()
            
            # 🔥 1차 / 2차 키워드 출력
            print("========== 상품명 생성 키워드 ==========")
            print("[1차 키워드]", p_keywords)
            print("[2차 키워드]", s_keywords)
            print("=======================================")

            # 3) LLM 요청
            from llm.llm_product_name_generator import generate_product_name_from_llm

            final_name = generate_product_name_from_llm(
                primary_keywords=p_keywords,
                secondary_keywords=s_keywords
            )

            # 4) 최종 상품명 입력란에 출력
            self.lens_final_name_text.delete("1.0", tk.END)
            self.lens_final_name_text.insert(tk.END, final_name)
            
            item.final_name = final_name

        except Exception as e:
            print("[상품명 생성 실패]", e)



    # =====================================================================
    # 상세보기 (즉시열림 + 4컬럼 + 캐싱 + 비동기 이미지 로딩 + 정렬/삭제)
    # =====================================================================
    def open_detail(self, item: ProductItem):
        print("\n========================")
        print("[DETAIL] 상세보기 클릭됨")
        print("========================")
        
        # 1) Toplevel 생성 직전
        print("[DETAIL] Toplevel 생성 시작")
        win = tk.Toplevel(self.root)
        
        print("[DETAIL] Toplevel 생성 완료")
        
        win.title("상품 상세정보")
        win.geometry("1500x900")
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
        content.columnconfigure(0, weight=2, uniform="col")
        content.columnconfigure(1, weight=2, uniform="col")
        content.columnconfigure(2, weight=2, uniform="col")
        content.columnconfigure(3, weight=3, uniform="col")
        content.rowconfigure(0, weight=1)
        print("[DETAIL] Grid 레이아웃 컬럼/로우 config 완료")

        # ============================================================
        # 1) 이미지 패널
        # ============================================================
        print("[DETAIL] 상품 이미지 패널 생성 시작")
        left = ttk.LabelFrame(content, text="상품 이미지", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

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
                    url, (120, 120),
                    lambda img, lbl=lbl: (
                        print(f"[ASYNC-CB] 콜백 실행 url={url[:60]}, 성공={img is not None}"),
                        lbl.configure(image=img, text="") if img else lbl.configure(text="[오류]"),
                        setattr(lbl, "image", img)
                    ), self.root
                )

                ttk.Button(row, text="삭제",
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
        # 2) 상품명 패널
        # ============================================================
        mid = ttk.LabelFrame(content, text="상품명", padding=10)
        mid.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        mid.grid_propagate(False)
        mid.pack_propagate(False)
        
        fixed_top = ttk.Frame(mid)
        fixed_top.pack(fill="x", pady=(0, 5))

        ttk.Label(fixed_top, text="최종 상품명").pack(anchor="w")

        self.lens_final_name_text = tk.Text(
            fixed_top,
            height=2,           # 최대 2줄 표시
            wrap="word",        # 단어 기준 줄바꿈
        )
        self.lens_final_name_text.pack(fill="x")
        
        category_text = "카테고리: 아직 선택되지 않음"
        if getattr(item, "category_name", None):
            if getattr(item, "category_code", None):
                category_text = f"카테고리: {item.category_name} ({item.category_code})"
            else:
                category_text = f"카테고리: {item.category_name}"

        self.category_result_label = ttk.Label(
            fixed_top,
            text=category_text,
            foreground="#333"
        )
        self.category_result_label.pack(anchor="w", pady=(5, 0))
        
        # 버튼 프레임
        btn_frame = ttk.Frame(fixed_top)
        btn_frame.pack(anchor="e", pady=5)
        
        # 카테고리 매칭 버튼
        ttk.Button(
            btn_frame,
            text="카테고리 매칭",
            command=lambda p=item: self.match_category_action(p)
        ).pack(side="right")
        
        ttk.Button(
            btn_frame,
            text="상품명 생성",
            command=lambda p=item: self.generate_product_name_action(p)
        ).pack(side="right", padx=5)

        # 초기값 설정
        initial_name = item.final_name or ""
        self.lens_final_name_text.insert("1.0", initial_name)

        c2 = tk.Canvas(mid)
        s2 = ttk.Scrollbar(mid, orient="vertical", command=c2.yview)
        inner2 = ttk.Frame(c2)
        bind_mousewheel(inner2, c2)
        inner2_id = c2.create_window((0, 0), window=inner2, anchor="nw")
        c2.configure(yscrollcommand=s2.set)

        c2.pack(fill="both", expand=True, side="left")
        s2.pack(fill="y", side="right")

        def on_resize_c2(e):
            c2.itemconfig(inner2_id, width=e.width)

        c2.bind("<Configure>", on_resize_c2)
        inner2.bind("<Configure>", lambda e: c2.configure(scrollregion=c2.bbox("all")))

        print("[DETAIL] Lens 패널 생성 시작")
        lens_list = item.lens_products
        print(f"[DETAIL] Lens 결과 로드 완료 (총 {len(lens_list)}개)")
        win.update()
        def refresh_lens():
            for w in inner2.winfo_children():
                w.destroy()

            for idx, p in enumerate(lens_list):
                row = ttk.Frame(inner2, padding=5)
                row.pack(fill="x", pady=5)

                # grid layout: 2 columns
                row.columnconfigure(0, weight=1)   # left expands
                row.columnconfigure(1, weight=0)   # button fixed

                # -----------------------------
                # LEFT AREA (image + text)
                # -----------------------------
                left_area = ttk.Frame(row)
                left_area.grid(row=0, column=0, sticky="nsew")

                # image
                lbl = ttk.Label(left_area, text="로딩중...")
                lbl.pack(side="left", padx=4)

                src = p.get("image", "")
                loader = (
                    load_image_async if src.startswith("http")
                    else load_base64_async
                )
                loader(
                    src, (80, 80),
                    lambda img, lbl=lbl: (
                        lbl.configure(image=img, text="") if img else lbl.configure(text="[오류]"),
                        setattr(lbl, "image", img)
                    ), self.root
                )

                # text label (wraplength will be updated later)
                text_lbl = ttk.Label(
                    left_area,
                    text=p.get("name", ""),
                    justify="left"
                )
                text_lbl.pack(side="left", padx=6, fill="x", expand=True)

                # -----------------------------
                # dynamically update wraplength
                # -----------------------------
                def update_wrap(event, lbl=text_lbl):
                    # left_area width - image area(80px) - padding(20px)
                    wrap_w = event.width - 120
                    if wrap_w < 50:
                        wrap_w = 50
                    lbl.configure(wraplength=wrap_w)

                left_area.bind("<Configure>", update_wrap)

                # -----------------------------
                # DELETE BUTTON
                # -----------------------------
                btn = ttk.Button(row, text="삭제", command=lambda i=idx: delete_lens(i))
                btn.grid(row=0, column=1, sticky="e", padx=5)


        def delete_lens(i):
            del lens_list[i]
            refresh_lens()

        refresh_lens()
        
        print("[DETAIL] 전체 패널 구성 완료")
        print("[DETAIL] 상세보기 창 준비 완료")

        # ============================================================
        # 3) 옵션 패널 (수정 가능 Entry 버전)
        # ============================================================
        opt = ttk.LabelFrame(content, text="옵션", padding=10)
        opt.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
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
                html_to_png_final
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
        detail.grid(row=0, column=3, sticky="nsew", padx=5, pady=5)
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
            text="상세설명 미리보기",
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

            # 왼쪽 Entry (원문 헤더)
            e_left = ttk.Entry(row, width=25)
            e_left.insert(0, h)
            e_left.pack(side="left", padx=5)
            left_entries.append(e_left)

            # -----------------------------
            # 오른쪽 Entry (매핑 후 헤더)
            # -----------------------------
            mapped = current_mapping.get(h)

            if mapped:
                display_val = mapped
                entry_style = "Mapped.TEntry"    # 매핑됨 → 검정
            else:
                display_val = translate_header(h)
                entry_style = "Translated.TEntry"  # 자동 번역 → 회색

            e_right = ttk.Entry(row, style=entry_style)
            e_right.insert(0, display_val)
            e_right.pack(side="left", fill="x", expand=True, padx=5)
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
            item.final_name = self.lens_final_name_text.get("1.0", "end").strip()
    
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
            item.lens_products = lens_list

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

        def task():
            for item in list(self.products_pending):

                result = self.scraper.collect(item.url)

                if "error" in result:
                    messagebox.showerror("오류", f"{item.url}\n{result['error']}")
                    continue

                # 🔥 파싱 + LLM 상세설명 생성 + 텍스트/HTML 변환 모두 load_data에서 끝남
                item.load_data(result)

                # 🔥 Lens 없음 경고만 유지
                if not item.lens_products:
                    messagebox.showwarning(
                        "Lens 없음",
                        f"Lens 데이터가 없습니다.\n({item.url})\n그래도 수집완료로 이동합니다."
                    )

                exists = any(c.url == item.url for c in self.products_collected)
                if not exists:
                    self.products_collected.append(item)

                self.refresh_tab_pending()
                self.refresh_tab_collected()

            messagebox.showinfo("완료", "수집이 완료되었습니다.")


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
