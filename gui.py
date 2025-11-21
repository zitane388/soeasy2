# gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from PIL import Image, ImageTk
import io, os, tempfile, subprocess
import threading, time, json
import base64
from websocket import create_connection

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
def get_cached_image(url, size=(160, 160)):
    key = (url, size)

    if key in IMAGE_CACHE:
        return IMAGE_CACHE[key]

    try:
        resp = requests.get(url, timeout=5)
        raw_img = Image.open(io.BytesIO(resp.content))
        img = resize_aspect_fit(raw_img, size)   # <<< 여기!!
        tki = ImageTk.PhotoImage(img)
        IMAGE_CACHE[key] = tki
        return tki
    except:
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
def load_image_async(url, size, callback, root):
    def task():
        img = get_cached_image(url, size)
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

        # -------------------------
        # 리스트 컨테이너 (여기만 refresh)
        # -------------------------
        self.list_container = ttk.Frame(self.collected_frame)
        self.list_container.pack(fill="both", expand=True)

        self.refresh_tab_collected()




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

            ttk.Label(row, text=item.url).pack(side="left", anchor="w")

            ttk.Button(row, text="삭제",
                       command=lambda p=item: self.delete_pending(p)
                       ).pack(side="right")

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

                load_image_async(item.thumbnail_url, (80, 80), cb, self.root)
            else:
                thumb_label.configure(text="[이미지 없음]")

            # 텍스트 영역
            text_frame = ttk.Frame(row)
            text_frame.pack(side="left", fill="x", expand=True)

            name_txt = item.final_name if item.final_name else "(상품명 미정)"
            desc_txt = item.final_description if item.final_description else "(상세설명 미정)"

            ttk.Label(text_frame, text=name_txt).pack(anchor="w")
            ttk.Label(text_frame, text=desc_txt[:80] + "...").pack(anchor="w")

            ttk.Button(row, text="상세보기",
                    command=lambda p=item: self.open_detail(p)
                    ).pack(side="right", padx=5)

            ttk.Button(row, text="삭제",
                    command=lambda p=item: self.delete_collected(p)
                    ).pack(side="right")

        self.update_tab_titles()



    # ==============================================================
    # 항목 추가
    # ==============================================================
    def add_product(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("알림", "URL을 입력해주세요.")
            return

        self.products_pending.append(ProductItem(url))
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
        # 1) 상세 HTML 생성
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
        # 실제 쇼핑몰 상세페이지 뷰 사이즈에 가장 가까운 900 × 1600
        try:
            subprocess.Popen([
                chrome_path,
                f'--app={file_url}',            # 📌 주소창/탭 없는 팝업 모드
                '--window-size=900,1600',       # 📌 정확한 사이즈 지정
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
            desc = item.final_description or item.parsed_raw.get("description") or ""
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

                ttk.Button(row, text="▲", width=3,
                        command=lambda i=idx: move_up(i)).pack(side="right")
                ttk.Button(row, text="▼", width=3,
                        command=lambda i=idx: move_down(i)).pack(side="right")
                ttk.Button(row, text="삭제",
                        command=lambda i=idx: delete_img(i)).pack(side="right")

        def move_up(i):
            if i > 0:
                images[i], images[i - 1] = images[i - 1], images[i]
                refresh_images()

        def move_down(i):
            if i < len(images) - 1:
                images[i], images[i + 1] = images[i + 1], images[i]
                refresh_images()

        def delete_img(i):
            del images[i]
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
        
        ttk.Button(
            fixed_top,
            text="상품명 생성",
            command=lambda p=item: self.generate_product_name_action(p)
        ).pack(anchor="e", pady=5)

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
        # 3) 옵션 패널
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

        # 색상
        ttk.Label(inner3, text="■ 색상 목록").pack(anchor="w", pady=4)
        for c in parsed.get("colors", []):
            r = ttk.Frame(inner3)
            r.pack(anchor="w", pady=3)

            if c.get("image"):
                lbl = ttk.Label(r, text="로딩중...")
                lbl.pack(side="left")
                load_image_async(
                    c["image"], (40, 40),
                    lambda img, lbl=lbl: (
                        lbl.configure(image=img, text="") if img else lbl.configure(text="[오류]"),
                        setattr(lbl, "image", img)
                    ), self.root
                )

            ttk.Label(r, text=f"{c['name']} ({c['code']})", wraplength=240).pack(side="left", padx=6)

        # 사이즈
        ttk.Label(inner3, text="\n■ 사이즈 목록").pack(anchor="w", pady=4)
        for s in parsed.get("sizes", []):
            ttk.Label(inner3, text=f"{s['name']} / disabled={s['disabled']}", wraplength=240).pack(anchor="w")

        # 가격
        ttk.Label(inner3, text="\n■ 가격 목록").pack(anchor="w", pady=4)
        for cd, price in parsed.get("prices", {}).items():
            ttk.Label(inner3, text=f"{cd}: {price}", wraplength=240).pack(anchor="w")

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
        detail_text = item.final_description or ""

        text_box = tk.Text(
            inner4,
            wrap="word",
            height=35,
            font=("맑은 고딕", 10)
        )
        text_box.pack(fill="x", padx=5, pady=10)

        # ▶ 정렬 태그 추가
        text_box.tag_configure("center", justify="center")

        # ▶ 텍스트 삽입
        text_box.insert("1.0", detail_text)

        # ▶ 전체 구간을 center 정렬 태그로 묶기
        text_box.tag_add("center", "1.0", "end")

        # ▶ 입력 변화 시에도 항상 가운데 정렬 유지
        def keep_center(*args):
            text_box.tag_add("center", "1.0", "end")

        text_box.bind("<KeyRelease>", keep_center)
        
        # ============================================================
        # 상세설명 저장 버튼
        # ============================================================
        def save_description():
            new_text = text_box.get("1.0", "end").strip()
            item.final_description = new_text

        ttk.Button(inner4, text="상세설명 저장", command=save_description).pack(pady=10)


        # ============================================================
        # 상세설명 HTML 미리보기 버튼 추가
        # ============================================================
        ttk.Button(
            inner4,
            text="상세설명 미리보기",
            command=lambda p=item: self.open_detail_description_preview(p)
        ).pack(pady=10)


        # ============================================================
        # 저장 버튼
        # ============================================================
        def save_all():
            # 수정된 상세설명 반영
            item.final_description = text_box.get("1.0", "end").strip()

            item.parsed_raw["images"] = images
            item.lens_products = lens_list
            win.destroy()
            self.refresh_tab_collected()

        ttk.Button(win, text="닫기", command=save_all).grid(row=1, column=0, pady=20)

            
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

                item.load_data(result)
                
                
                if not item.final_description:
                    original_desc = item.parsed_raw.get("detail_description")
                    if original_desc:
                        from llm.llm_detail_generator import generate_sections_from_llm
                        print("[LLM] 상세설명 생성:", item.url)
                        item.final_description = generate_sections_from_llm(original_desc)

                if not item.lens_products:
                    messagebox.showwarning(
                        "Lens 없음",
                        f"Lens 데이터가 없습니다.\n({item.url})\n그래도 수집완료로 이동합니다."
                    )

                exists = any(c.url == item.url for c in self.products_collected)
                if not exists:
                    self.products_collected.append(item)

                # ▶ 대기 리스트는 삭제하지 않음
                # self.products_pending.remove(item)

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
    root.geometry("1600x900")
    app = ProductCollectorGUI(root)
    root.mainloop()
