import logging
import csv
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from naver_best.orchestrator import NaverBestOrchestrator
from naver_best.models import NaverProductItem
from scrapers.scraper_factory import ScraperFactory

class NaverBestPage:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.urls_from_store = []
        self.check_vars = {} # 체크박스 및 이미지 선택 상태 저장
        self.items = []
        self.orchestrator = None
        self.collect_thread = None

    def build(self):
        # --- 상단 헤더 섹션 ---
        header = ttk.Frame(self.frame)
        header.pack(fill="x", pady=(10, 5), padx=20)
        
        top_buttons = ttk.Frame(header)
        top_buttons.pack(fill="x", side="top", pady=(0, 10))
        
        self.btn_load = ttk.Button(top_buttons, text="상점 불러오기", command=self.load_store_csv)
        self.btn_load.pack(side="left", padx=(0, 8))

        self.btn_collect_list = ttk.Button(top_buttons, text="베스트상품 수집 시작", command=self.start_collect_list)
        self.btn_collect_list.pack(side="left", padx=(0, 8))
        
        self.btn_collect_detail = ttk.Button(top_buttons, text="상세상품 수집 시작", command=self.start_collect_detail)
        self.btn_collect_detail.pack(side="left", padx=(0, 8))
        
        self.btn_origin = ttk.Button(top_buttons, text="원본상품 수집", command=self.start_origin_collect)
        self.btn_origin.pack(side="left")

        # --- 전체 선택 체크박스 영역 ---
        bottom_header = ttk.Frame(header)
        bottom_header.pack(fill="x", side="top")
        self.all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bottom_header, text=" 페이지 전체 선택", variable=self.all_var, 
                        command=self._toggle_all).pack(side="left")

        # --- 스크롤 가능한 리스트 컨테이너 (기존 구조 유지) ---
        outer_container = ttk.Frame(self.frame)
        outer_container.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = tk.Canvas(outer_container, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(outer_container, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.list_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")

        # 리스트 내용 변경 시 스크롤 업데이트 및 폭 맞춤
        self.list_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _toggle_all(self):
        """전체 선택 체크박스 로직"""
        val = self.all_var.get()
        for res in self.check_vars.values():
            res['main'].set(val)

    def _safe_status(self, msg):
        """부모 app의 _status 유무를 체크하여 안전하게 호출"""
        if hasattr(self.app, '_status'):
            self.app._status(msg)
        else:
            logging.info(f"[STATUS] {msg}")

    def load_store_csv(self):
        """data/store.csv 파일 로드"""
        path = Path("data/store.csv")
        if not path.exists():
            messagebox.showwarning("알림", "data/store.csv 파일을 찾을 수 없습니다.")
            return

        try:
            with path.open("r", encoding="utf-8") as f:
                urls = [row[0].strip() for row in csv.reader(f) if row and row[0].startswith("http")]
            
            self.urls_from_store = urls
            self.btn_load.config(text=f"상점 불러오기({len(urls)}개) 완료")
            self._safe_status(f"상점 URL {len(urls)}개 로드 완료")

        except Exception as e:
            messagebox.showerror("오류", f"CSV 읽기 실패: {e}")

    # gui/pages/naver_best_page.py
    def start_collect_list(self):
        """베스트 상품 목록 수집 시작 (기존 버튼 1)"""
        if not self.urls_from_store:
            messagebox.showwarning("알림", "먼저 상점 URL을 설정해주세요.")
            return

        self.btn_collect_list.config(state="disabled", text="목록 수집 중...")
        self.items.clear() # 새 목록을 위해 비움
        
        # 오케스트레이터 초기화 (기존 코드와 동일)
        self.orchestrator = NaverBestOrchestrator(
            urls_from_store=self.urls_from_store,
            stop_event=threading.Event(),
            items_container=self.items
        )
        self._setup_orchestrator_callbacks() # 콜백 등록 로직을 별도로 빼두면 좋습니다

        # 목록 수집 스레드 실행
        threading.Thread(target=self.orchestrator.collect_list_only, daemon=True).start()

    def start_collect_detail(self):
        """상세상품 수집 시작 (새로 추가된 버튼 2)"""
        if not self.items:
            messagebox.showwarning("알림", "수집된 목록이 없습니다.")
            return

        self.btn_collect_detail.config(state="disabled", text="상세 수집 중...")
        
        # 기존에 생성된 오케스트레이터를 사용하여 상세 수집만 실행
        threading.Thread(target=self.orchestrator.collect_details_only, daemon=True).start()

    def _setup_orchestrator_callbacks(self):
        """콜백 함수 등록 유틸리티"""
        self.orchestrator._render_cards = lambda: self.frame.after(0, self.refresh_ui_list)
        self.orchestrator._status = lambda msg: self.frame.after(0, lambda: self._safe_status(msg))
        self.orchestrator._refresh_buttons = lambda: self.frame.after(0, self.on_collect_finished)
    

    def start_origin_collect(self):
        """선택된 대표 이미지 → Google Lens HTML 수집"""
        if not self.items:
            messagebox.showwarning("알림", "수집된 베스트 상품이 없습니다.")
            return

        self._safe_status("Google Lens 소싱 시작...")

        def worker():
            factory = ScraperFactory()
            lens_scraper = factory.get_lens_scraper()

            count = 0

            for idx, item in enumerate(self.items, start=1):
                vars_map = self.check_vars.get(idx)
                if not vars_map:
                    continue

                # 체크 안된 상품 제외
                if not vars_map['main'].get():
                    continue

                img_idx = vars_map['img_select'].get()
                imgs = getattr(item, 'images', [])

                if not imgs or img_idx >= len(imgs) or not imgs[img_idx]:
                    continue

                img_url = imgs[img_idx]
                print(f"\n🔍 Lens 검색 시작: {img_url}")

                html = lens_scraper.search(img_url)

                if html:
                    print("📦 Lens HTML 수집 완료", len(html))
                    # 👉 다음 단계: 여기서 Lens 결과 파싱 가능
                else:
                    print("❌ Lens 수집 실패")

                count += 1

            self.frame.after(0, lambda: self._safe_status(f"Lens 검색 {count}개 완료"))

        threading.Thread(target=worker, daemon=True).start()


    def on_collect_finished(self):
        # 이 부분이 실행되어야 버튼이 '상세 수집 중...'에서 '상세상품 수집 시작'으로 돌아옵니다.
        self.btn_collect_list.config(text="베스트상품 수집 시작", state="normal")
        self.btn_collect_detail.config(text="상세상품 수집 시작", state="normal") # 필수!
        messagebox.showinfo("완료", "모든 데이터 수집이 완료되었습니다.")

    def refresh_ui_list(self):
        """수집 중 호출되는 콜백"""
        self.refresh() # 위에서 수정한 refresh를 호출하여 중복 코드 방지
        """수집된 데이터를 바탕으로 리스트 화면 갱신"""
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        if not self.items:
            tk.Label(self.list_frame, text="수집된 상품이 없습니다.", fg="gray").pack(pady=20)
        else:
            for idx, item in enumerate(self.items, 1):
                self.render_row_with_data(idx, item)
                
    def refresh(self):
        """리스트 영역을 비우고 데이터를 다시 렌더링"""
        if hasattr(self, 'list_frame'):
            for child in self.list_frame.winfo_children():
                child.destroy()

        if not hasattr(self, 'check_vars'):
            self.check_vars = {}

        # [수정] self.items를 우선 참조하고, 없으면 app 데이터를 참조
        target_items = self.items if self.items else getattr(self.app, 'naver_best_items', [])

        if not target_items:
            empty_lbl = ttk.Label(
                self.list_frame, 
                text="수집된 베스트 상품이 없습니다.",
                foreground="#888"
            )
            empty_lbl.pack(pady=100)
            return

        for idx, item in enumerate(target_items, start=1):
            try:
                self.render_row_with_data(idx, item)
            except Exception as e:
                print(f"Row 렌더링 에러 ({idx}): {e}")

    def render_row_with_data(self, index: int, item: NaverProductItem):
        """순위/체크박스를 좌측 중앙에, 이미지와 정보를 우측에 배치하는 레이아웃"""
        from gui.widgets.image_loader import load_image_async

        # 1. 상태 변수 설정
        main_v = tk.BooleanVar(value=True)
        img_selection = tk.IntVar(value=0)
        self.check_vars[index] = {'main': main_v, 'img_select': img_selection}

        # 2. 컨테이너 설정
        item_container = ttk.Frame(self.list_frame)
        item_container.pack(fill="x")

        row = ttk.Frame(item_container)
        row.pack(fill="x", pady=15, padx=20)

        # --- [우측 섹션] 버튼 및 상태 정보 (기존 유지) ---
        right_section = ttk.Frame(row)
        right_section.pack(side="right", fill="y")
        
        btn_area = ttk.Frame(right_section)
        btn_area.pack(side="right", padx=(20, 0))
        
        ttk.Button(btn_area, text="후보상품보기", width=12).pack(pady=2, side="top")
        ttk.Button(
            btn_area, 
            text="삭제", 
            width=12, 
            command=lambda target=item: self.delete_single_item(target)
        ).pack(pady=2, side="top")

        info_area = ttk.Frame(right_section)
        info_area.pack(side="right", fill="y", padx=10)
        ttk.Frame(info_area).pack(expand=True) 

        collect_status = "완료" if getattr(item, 'is_collected', False) else "수집중"
        ttk.Label(info_area, text=f"베스트상품 수집: {collect_status}").pack(anchor="w")
        ttk.Label(info_area, text=f"원본상품 수집: 대기").pack(anchor="w", pady=(2, 0))
        ttk.Label(info_area, text="최종 선정: 대기").pack(anchor="w", pady=(2, 0))
        ttk.Frame(info_area).pack(expand=True)

        tk.Frame(row, width=1, bg="#e0e0e0").pack(side="right", fill="y", padx=20)

        # --- [좌측 섹션] 구조 개편 ---
        left = ttk.Frame(row)
        left.pack(side="left", fill="both", expand=True)

        # A. 최좌측 영역: 숫자와 체크박스를 세로 중앙 정렬
        left_edge = ttk.Frame(left)
        left_edge.pack(side="left", fill="y", padx=(0, 20)) # 이미지와의 간격 확보

        edge_center = ttk.Frame(left_edge)
        edge_center.pack(expand=True) # 위아래 공간을 균등하게 채워 중앙 배치 효과

        ttk.Label(edge_center, text=f"{index}.", width=3, font=("맑은 고딕", 12, "bold")).pack(side="left")
        ttk.Checkbutton(edge_center, variable=main_v).pack(side="left", padx=(2, 0))
        
        # B. 메인 컨텐츠 영역: 상단(이미지들) + 하단(상품정보)
        content_area = ttk.Frame(left)
        content_area.pack(side="left", fill="both", expand=True)

        # B-1. 상단 이미지 슬롯
        top_img_row = ttk.Frame(content_area)
        top_img_row.pack(fill="x", anchor="w")

        imgs = getattr(item, 'images', [])
        for i in range(5):
            slot = ttk.Frame(top_img_row)
            slot.pack(side="left", padx=(0, 10)) # 이미지 사이 간격
            
            rb = tk.Radiobutton(slot, variable=img_selection, value=i)
            rb.pack(anchor="nw")
            
            img_box = tk.Frame(slot, width=100, height=100, bg="#ffffff", highlightthickness=0, borderwidth=0)
            img_box.pack(side="top")
            img_box.pack_propagate(False)

            thumb_label = tk.Label(img_box, text="[대기]", bg="#ffffff", borderwidth=0, highlightthickness=0)
            thumb_label.pack(expand=True, fill="both")
            thumb_label.bind("<Button-1>", lambda e, val=i: img_selection.set(val))

            def img_cb(img, lbl=thumb_label):
                try:
                    if lbl.winfo_exists(): 
                        if img:
                            lbl.config(image=img, text="")
                            lbl.image = img 
                        else:
                            lbl.config(text="[실패]")
                except (tk.TclError, RuntimeError):
                    pass

            if i < len(imgs) and imgs[i]:
                thumb_label.config(text="[로드중]")
                load_image_async(imgs[i], (100, 100), img_cb, self.app.root)
            else:
                thumb_label.config(text="[미수집]")

        # B-2. 하단 정보 (상품명 및 옵션)
        p_name = item.name if item.name else "상품명 없음"
        is_done = getattr(item, 'is_collected', False)

        if is_done and hasattr(item, 'variants') and item.variants:
            all_opts = []
            for v in item.variants:
                opt_map = getattr(v, 'option_map', {}) if not isinstance(v, dict) else v.get('option_map', {})
                for g, val in opt_map.items():
                    all_opts.append(f"{g}: {val}")
            unique_opts = list(dict.fromkeys(all_opts))
            if unique_opts:
                opt_display = ", ".join(unique_opts[:4]) + (f" 외 {len(unique_opts)-4}개" if len(unique_opts) > 4 else "")
            else:
                opt_display = "옵션 없음"
        else:
            opt_display = "대기" if not is_done else "옵션 정보 없음"

        desc_text = f"{len(item.description)}자" if item.description else "0자"
        info_str = f"상품명: {p_name}\n옵션: {opt_display} | 상세설명: {desc_text}"
        
        # 이제 content_area에 붙으므로 첫 번째 이미지의 왼쪽 끝과 자동으로 정렬됩니다.
        ttk.Label(content_area, text=info_str, foreground="#333", wraplength=600, justify="left").pack(
            anchor="w", pady=(15, 0)
        )

        tk.Frame(item_container, height=1, bg="#e0e0e0").pack(fill="x", padx=20)
        
    def show(self):
        """페이지를 화면에 표시"""
        # [수정] 리스트 프레임에 자식 요소가 없을 때만(처음이거나 삭제 후일 때만) 새로고침
        if hasattr(self, 'list_frame') and not self.list_frame.winfo_children():
            self.refresh()
        
        # 이미 데이터가 그려져 있다면 refresh를 건너뛰고 팩(Pack)만 함
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """페이지를 화면에서 숨김"""
        self.frame.pack_forget()
        
    def delete_single_item(self, target):
        """특정 항목 하나만 제거"""
        if not target:
            return

        # 1. 현재 페이지의 리스트에서 제거 (실제 UI 데이터 소스)
        if target in self.items:
            self.items.remove(target)
        
        # 2. 메인 앱 저장소와 동기화 (만약 존재한다면)
        if hasattr(self.app, 'naver_best_items') and target in self.app.naver_best_items:
            self.app.naver_best_items.remove(target)

        # 3. UI 즉시 갱신
        self.refresh()