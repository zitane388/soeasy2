# gui/product_detail/name_panel.py

import json, os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageOps
import urllib.request, io, threading
from utils.path import p

from gui.widgets.scroll_frame import ScrollFrame
from gui.widgets.thumbnail_helper import load_thumbnail_async
from gui.widgets.image_loader import load_image_async
from image_tools.image_source_resolver import resolve_item_image_sources

from pname_keyword import extract_keywords
from utils.product_name_generator import generate_final_name
from category.matcher.auto_category_pipeline import auto_match_category

from category.matcher.category_matcher import match_category_from_json, get_smartstore_category_code


class NamePanel(ttk.LabelFrame):

    def __init__(self, parent, item, owner):
        super().__init__(parent, text="상품명/카테고리/속성", padding=10)

        self.owner = owner
        self.item = item
        # ============================================================
        # ScrollFrame 적용
        # ============================================================
        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True)
        self.inner = sf.inner

        self.build_ui()

    # ============================================================
    # UI 구축
    # ============================================================
    def build_ui(self):
        inner2 = self.inner
        item = self.item

        # ------------------------------------------------------------
        # (A) 이미지 목록
        # ------------------------------------------------------------
        self.selected_main_image = tk.StringVar()
        self._grid_img_cache = []

        self._selected_windly_category = None
        self._current_mode = None

        # ================================
        # 1. 옵션 이미지 URL 수집
        # ================================
        option_image_urls = set()
        for opt in item.parsed_raw.get("options", []):
            for v in opt.get("values", []):
                img = v.get("image")
                if isinstance(img, str) and img.startswith("http"):
                    option_image_urls.add(img)

        # ================================
        # 2. file_path → original_url 매핑
        # ================================
        file_to_original_url = {}
        logo_results = getattr(item, "logo_job_results", None)
        if isinstance(logo_results, list):
            for r in logo_results:
                url = r.get("url")
                fp = r.get("file_path")
                if url and fp:
                    file_to_original_url[os.path.abspath(fp)] = url

        def is_option_image(src: str) -> bool:
            if src.startswith("http"):
                return src in option_image_urls

            src_abs = os.path.abspath(src)
            original_url = file_to_original_url.get(src_abs)
            if original_url:
                return original_url in option_image_urls

            return False

        # ================================
        # 3. 이미지 소스 결정 (중요)
        # ================================
        sources = resolve_item_image_sources(item)

        all_imgs = []
        for src in sources:
            if not isinstance(src, str):
                continue
            if is_option_image(src):
                continue
            all_imgs.append(src)

        try:
            local_cnt = sum(1 for u in all_imgs if isinstance(u, str) and os.path.exists(u))
            print(f"[DETAIL] 이미지 {len(all_imgs)}개 (옵션 제외) local={local_cnt} url={len(all_imgs)-local_cnt}")
            for i, u in enumerate(all_imgs[:6]):
                flag = "LOCAL" if isinstance(u, str) and os.path.exists(u) else "URL"
                print(f"[DETAIL] src[{i}] {flag} {u}")
        except Exception as e:
            print("[DETAIL] image source log failed:", e)

        # ================================
        # 4. UI 렌더링
        # ================================
        COLUMN = 4
        THUMB = (80, 80)
        MAX_IMAGES = 8

        def toggle_radio(v):
            cur = self.selected_main_image.get()
            self.selected_main_image.set("" if cur == v else v)

        row = col = 0
        root = inner2.winfo_toplevel()

        for src in all_imgs[:MAX_IMAGES]:
            cell = ttk.Frame(inner2, padding=0)
            cell.grid(row=row, column=col, sticky="nsew", padx=1, pady=1)

            rb = ttk.Radiobutton(cell, variable=self.selected_main_image, value=src)
            rb.pack(anchor="center")

            lb = ttk.Label(cell, text="loading...")
            lb.pack()

            rb.bind("<Button-1>", lambda e, v=src: toggle_radio(v))
            lb.bind("<Button-1>", lambda e, v=src: toggle_radio(v))
            cell.bind("<Button-1>", lambda e, v=src: toggle_radio(v))

            def cb(photo, label=lb):
                if not label.winfo_exists():
                    return
                if photo:
                    label.config(image=photo, text="")
                    label.image = photo
                else:
                    label.config(text="LOAD_FAIL")

            if isinstance(src, str) and src.startswith("http"):
                load_thumbnail_async(src, THUMB, cb, root)
            else:
                load_image_async(src, THUMB, cb, root)

            col += 1
            if col == COLUMN:
                col = 0
                row += 1



        img_end_row = row
        inner2.columnconfigure(0, weight=1)
        row = img_end_row + 1

        # ------------------------------------------------------------
        # (B) 키워드 영역
        # ------------------------------------------------------------
        keyword_frame = ttk.Frame(inner2, padding=5)
        keyword_frame.grid(row=row, column=0, columnspan=4,
                           sticky="ew", pady=(0,10))

        self.keyword_textbox = tk.Text(keyword_frame, height=12, wrap="word")
        self.keyword_textbox.pack(fill="x")

        keywords = item.name_keywords if getattr(item, "name_keywords", None) else []
        if keywords:
            self.keyword_textbox.insert("1.0", ", ".join(keywords))

        def refresh_keywords():
            current_name = self.final_name_text.get("1.0", "end").strip()
            if not current_name:
                print("[KEYWORD] 상품명 없음 → 수집 불가")
                return

            new_keywords = extract_keywords(current_name, item.brand)
            item.name_keywords = new_keywords
            self.keyword_textbox.delete("1.0", "end")
            self.keyword_textbox.insert("1.0", ", ".join(new_keywords))
            print("[KEYWORD UPDATED]", new_keywords)

        ttk.Button(keyword_frame, text="키워드 수집",
                   command=refresh_keywords).pack(anchor="w", pady=(6,0))

        row += 2

        # ------------------------------------------------------------
        # (C) 원본 상품명
        # ------------------------------------------------------------
        orig_name = getattr(item, "original_ko_name", "(원본 없음)")
        orig_label = tk.Text(inner2, height=2, wrap="word", bg="#eee")
        orig_label.insert("1.0", orig_name)
        orig_label.config(state="disabled")
        orig_label.grid(row=row, column=0, columnspan=4,
                        sticky="ew", padx=5, pady=(5,10))

        row += 2

        # ------------------------------------------------------------
        # (D) 최종 상품명 입력
        # ------------------------------------------------------------
        ttk.Label(inner2, text="■ 최종 상품명").grid(
            row=row, column=0, columnspan=4, sticky="w", pady=(10,0)
        )
        row += 1

        name_frame = ttk.Frame(inner2, padding=(0,10))
        name_frame.grid(row=row, column=0, columnspan=4, sticky="ew")

        self.final_name_text = tk.Text(name_frame, height=2, wrap="word")
        self.final_name_text.pack(fill="x")

        def generate_product_name_action(item):
            translated_name = item.original_name or item.parsed_raw.get("original_name") or ""
            raw_keywords = self.keyword_textbox.get("1.0", "end").strip()
            keywords = [
                kw.strip()
                for kw in raw_keywords.replace("\n", " ").split(",")
                if kw.strip()
            ]

            if not translated_name:
                print("[ERROR] 원본상품명 없음")
                return
            if not keywords:
                print("[ERROR] 키워드 없음")
                return

            selected_img = self.selected_main_image.get() or None
            print(f"[IMG SELECT] {selected_img}")

            # 🔒 버튼 비활성화 (선택)
            # btn_generate.config(state="disabled")

            def task():
                try:
                    new_name = generate_final_name(
                        product_item=item,        # 🔥 반드시 첫 번째지만 키워드로 전달 가능
                        translated_name=translated_name,
                        keyword_list=keywords,
                        image_url=selected_img,
                    )


                    if not new_name:
                        print("[상품명 실패] 결과 없음")
                        return

                    def apply_ui():
                        item.final_name = new_name
                        self.final_name_text.delete("1.0", "end")
                        self.final_name_text.insert("1.0", new_name)
                        print(f"[FINAL NAME] {new_name}")

                        # btn_generate.config(state="normal")

                    # ✅ UI 갱신은 반드시 after
                    self.after(0, apply_ui)

                except Exception as e:
                    print("[NAME LLM ERROR]", e)
                    # self.after(0, lambda: btn_generate.config(state="normal"))

            import threading
            threading.Thread(target=task, daemon=True).start()


        ttk.Button(name_frame, text="상품명 생성",
                   command=lambda p=item: generate_product_name_action(p))\
            .pack(anchor="w", pady=5)

        initial = item.final_name or ""
        self.final_name_text.insert("1.0", initial)

        row += 3
        
        separator = ttk.Separator(inner2, orient="horizontal")
        separator.grid(
            row=row,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(12, 12)
        )

        row += 1
        
        # ------------------------------------------------------------
        # (F) 윈들리 카테고리 검색 영역
        # ------------------------------------------------------------
        ttk.Label(inner2, text="■ 카테고리 설정").grid(
            row=row + 7, column=0, columnspan=4,
            sticky="w", pady=(10, 0)
        )

        category_frame = ttk.Frame(inner2, padding=(0, 10))
        category_frame.grid(
            row=row + 8, column=0, columnspan=4,
            sticky="ew"
        )

        # category_frame 내부는 grid만 사용
        category_frame.columnconfigure(1, weight=1)  # 검색창 확장

        # 1행: 자동매칭 버튼(왼쪽) + 검색창(가운데 확장) + 적용 버튼(오른쪽)
        self.auto_match_btn = ttk.Button(
            category_frame,
            text="자동매칭",
            command=self.run_category_auto_match
        )
        self.auto_match_btn.grid(row=0, column=0, sticky="w")

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(category_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        # --------------------------------------------------
        # 결과 리스트 + 스크롤바
        # --------------------------------------------------
        result_frame = ttk.Frame(category_frame)
        result_frame.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(8, 0)
        )

        category_frame.rowconfigure(1, weight=1)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        result_box = tk.Listbox(
            result_frame,
            height=10,
            activestyle="none"
        )
        
        # --------------------------------------------------
        # 마우스 휠 스크롤 지원 (Windows / macOS / Linux)
        # --------------------------------------------------
        def _on_mousewheel(event):
            # Windows / macOS
            if event.delta:
                result_box.yview_scroll(int(-1 * (event.delta / 120)), "units")
            # Linux
            elif event.num == 4:
                result_box.yview_scroll(-1, "units")
            elif event.num == 5:
                result_box.yview_scroll(1, "units")

            return "break"   # 🔥 핵심: 이벤트 전파 차단


        # Windows / macOS
        result_box.bind("<MouseWheel>", _on_mousewheel)
        # Linux
        result_box.bind("<Button-4>", _on_mousewheel)
        result_box.bind("<Button-5>", _on_mousewheel)
        
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)

        result_box.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=result_box.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        result_box.config(yscrollcommand=scrollbar.set)


        def on_direct_select(event):
            idx = result_box.nearest(event.y)
            if idx is None:
                return

            selected_text = result_box.get(idx)

            if not (selected_text.startswith("[") and selected_text.endswith("]")):
                return

            template_key = selected_text.strip("[]").strip()

            target = None
            for entry in self._windly_cache:
                if entry.get("template_key") == template_key:
                    target = entry
                    break
            if not target:
                return

            categories = target.get("categories", {})
            smartstore_path = categories.get("스마트스토어 카테고리")
            if not smartstore_path:
                return

            market = "스마트스토어 카테고리"

            # --------------------------------------------------
            # 1️⃣ 카테고리 즉시 확정 (UI 스레드)
            # --------------------------------------------------
            from category.matcher.category_matcher import (
                get_smartstore_category_code,
                normalize_smartstore_path,
            )

            normalized_path = normalize_smartstore_path(smartstore_path)
            category_code = get_smartstore_category_code(normalized_path)

            self.item.category_name = smartstore_path
            self.item.category_code = category_code
            self.item.matched_category_template_key = template_key
            self._selected_windly_category = (market, smartstore_path)
            self._windly_applied = True

            print(
                "[MANUAL APPLY]",
                "path =", smartstore_path,
                "code =", category_code
            )

            self.final_category_label.config(
                text=f"[수동매칭] {template_key}\n{market} > {smartstore_path}",
                foreground="#1a1a1a"
            )

            # --------------------------------------------------
            # 2️⃣ 속성 자동 매칭 (비동기)
            # --------------------------------------------------
            product_name = (
                self.final_name_text.get("1.0", "end").strip()
                or self.item.final_name
                or ""
            )

            option_names = [
                v.get("name")
                for opt in self.item.parsed_raw.get("options", [])
                for v in opt.get("values", [])
                if v.get("name")
            ]

            detail_text = getattr(self.item, "final_detail_text", "") or ""

            selected_img = self.selected_main_image.get()
            image_urls = (
                [selected_img]
                if selected_img
                else ([self.item.thumbnail_url] if self.item.thumbnail_url else [])
            )

            def task():
                try:
                    self._apply_category_and_prefetch_attributes(
                        product_name=product_name,
                        option_names=option_names,
                        detail_text=detail_text,
                        image_urls=image_urls,
                    )
                except Exception as e:
                    print("[ATTR ERROR]", e)

            import threading
            threading.Thread(target=task, daemon=True).start()


        result_box.bind("<Double-Button-1>", on_direct_select)

        def search_direct_categories(event=None):
            keyword = self.search_var.get().strip()
            result_box.delete(0, "end")

            if not keyword:
                return

            # 캐시 로딩
            if not hasattr(self, "_windly_cache"):
                json_path = p("category", "sources", "windly", "windly_categories.json")
                if not os.path.exists(json_path):
                    result_box.insert("end", "윈들리 카테고리 파일 없음")
                    return

                with open(json_path, "r", encoding="utf-8") as f:
                    self._windly_cache = json.load(f)

            keyword_lower = keyword.lower()

            # ✅ template_key만 비교해서 검색
            matched_keys = []
            for entry in self._windly_cache:
                template_key = (entry.get("template_key") or "").strip()
                if not template_key:
                    continue

                if keyword_lower in template_key.lower():
                    matched_keys.append(template_key)

            if not matched_keys:
                result_box.insert("end", "검색 결과 없음")
                return

            # 상태 저장
            self._template_keys_shown = matched_keys
            self._current_mode = "template"

            # 결과 표시
            for key in matched_keys:
                result_box.insert("end", f"[{key}]")


        search_entry.bind("<Return>", search_direct_categories)

        
        final_row = row + 9

        final_title = ttk.Label(
            inner2,
            text="■ 최종 카테고리"
        )
        final_title.grid(
            row=final_row,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(10, 0)
        )

        final_category_frame = ttk.Frame(inner2, padding=(5,0))
        final_category_frame.grid(
            row=final_row + 1,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(4, 0)
        )

        self.final_category_label = ttk.Label(
            final_category_frame,
            text="",
            foreground="#2a2a2a"
        )
        self.final_category_label.pack(anchor="w")
        
        self._windly_applied = False
        
        # ------------------------------------------------------------
        # (INIT) 기존 카테고리 값이 있으면 UI에 반영
        # ------------------------------------------------------------
        if getattr(item, "category_name", None):
            path = item.category_name
            code = getattr(item, "category_code", None)

            template_key = getattr(item, "matched_category_template_key", None)

            label = ""

            if template_key:
                label += f"[매칭기준] {template_key}\n"

            label += f"스마트스토어 카테고리 > {item.category_name}"

            self.final_category_label.config(
                text=label,
                foreground="#1a1a1a"
            )

            # 내부 상태도 동기화
            self._selected_windly_category = ("스마트스토어 카테고리", path)
            self._windly_applied = True

            print("[INIT] 기존 카테고리 UI 반영:", path)
        
        separator2 = ttk.Separator(inner2, orient="horizontal")
        separator2.grid(
            row=final_row + 2,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(24, 12)
        )
            
        from gui.product_detail.attribute_panel import AttributePanel

        self.attribute_panel = AttributePanel(
            self.inner,
            item
        )
        self.attribute_panel.grid(
            row=final_row + 3,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=10
        )


        
    def pick_preferred_category(self, categories: dict):
        """
        windly_categories.json의 categories에서
        UI에 적용할 대표 카테고리를 고른다.

        우선순위:
        1) 스마트스토어 카테고리
        2) 네이버 카테고리(혹시 키가 바뀌는 경우 대비)
        3) 쿠팡 카테고리
        4) 그 외 아무거나(마지막 fallback)
        """
        if not isinstance(categories, dict) or not categories:
            return None, None

        preferred_keys = [
            "스마트스토어 카테고리",
            "네이버 카테고리",
            "쿠팡 카테고리",
        ]

        for k in preferred_keys:
            v = categories.get(k)
            if isinstance(v, str) and v.strip():
                return k, v.strip()

        # fallback: 첫 유효 항목
        for k, v in categories.items():
            if isinstance(v, str) and v.strip():
                return k, v.strip()

        return None, None

        
    def run_category_auto_match(self):
        print("\n==============================")
        print("[AUTO-MATCH] 카테고리 자동매칭 시작")
        print("==============================")

        item = self.item

        # ----------------------------------
        # 입력값 수집 (메인 스레드)
        # ----------------------------------
        product_name = (
            self.final_name_text.get("1.0", "end").strip()
            or item.final_name
            or ""
        )

        detail_text = getattr(item, "final_detail_text", "") or ""

        option_names = [
            v.get("name")
            for opt in item.parsed_raw.get("options", [])
            for v in opt.get("values", [])
            if v.get("name")
        ]

        selected_img = self.selected_main_image.get() or None
        image_urls = (
            [selected_img]
            if selected_img
            else ([item.thumbnail_url] if item.thumbnail_url else [])
        )

        # ----------------------------------
        # UI 상태 표시 (즉시)
        # ----------------------------------
        self.final_category_label.config(
            text="카테고리 자동매칭 중...",
            foreground="#777"
        )

        # ----------------------------------
        # 백그라운드 작업
        # ----------------------------------
        def task():
            try:
                result = auto_match_category(
                    product_name=product_name,
                    option_names=option_names,
                    detail_text=detail_text,
                    image_urls=image_urls,
                )
            except Exception as e:
                result = {"error": str(e)}

            # ----------------------------------
            # UI 반영은 반드시 메인 스레드
            # ----------------------------------
            def apply_result():
                if not result or "error" in result:
                    item.matched_category_template_key = None 
                    self.final_category_label.config(
                        text="자동 매칭 결과 없음",
                        foreground="red"
                    )
                    return

                item.category_name = result["category_name"]
                item.category_code = result["category_code"]
                item.matched_category_template_key = result.get("template_key")
                self._windly_applied = True

                self.final_category_label.config(
                    text=(
                        f"[자동매칭] {result['template_key']}\n"
                        f"스마트스토어 카테고리 > {item.category_name}"
                    ),
                    foreground="#1a1a1a",
                )

                print("[DONE] 카테고리 자동매칭 완료")

                # 🔥 속성 자동 매칭도 여기서 실행 (이미 비동기 안전)
                self._apply_category_and_prefetch_attributes(
                    product_name=product_name,
                    option_names=option_names,
                    detail_text=detail_text,
                    image_urls=image_urls,
                )

            self.after(0, apply_result)

        import threading
        threading.Thread(target=task, daemon=True).start()


        
    def _apply_category_and_prefetch_attributes(
        self,
        *,
        product_name: str,
        option_names: list[str],
        detail_text: str,
        image_urls: list[str],
    ):
        item = self.item

        # SmartStore 세션
        app = self.owner.get_app()
        session = app.ensure_smartstore_session()

        from category.services.attribute_prefetch import prefetch_category_attributes

        prefetch_category_attributes(
            item=item,
            session=session,
            product_name=product_name,
            option_names=option_names,
            detail_text=detail_text,
            image_urls=image_urls,
        )

        # UI 반영
        self.attribute_panel.set_schema(item.attribute_schema)
        self.attribute_panel.set_matched(item.attribute_matched)


    # ============================================================
    # SAVE
    # ============================================================
    def save(self):
        item = self.item

        # ----------------------------
        # 상품명
        # ----------------------------
        item.final_name = self.final_name_text.get("1.0", "end").strip()

        # ----------------------------
        # 키워드
        # ----------------------------
        raw_kw = self.keyword_textbox.get("1.0", "end").strip()
        kw_list = [k.strip() for k in raw_kw.replace("\n", " ").split(",") if k.strip()]
        item.name_keywords = kw_list

        # ----------------------------
        # 🔥 카테고리 확정 (필수)
        # ----------------------------
        if not getattr(item, "category_code", None):
            print("[SAVE WARNING] category_code 없음")
            return False

        # ----------------------------
        # 🔥 속성 확정
        # ----------------------------
        attr_state = self.attribute_panel.collect_current_values()
        item.attribute_matched = attr_state["matched"]
        item.attribute_payload = attr_state["payload"]

        print("[SAVE] category_code =", item.category_code)
        print("[SAVE] attribute_payload =", item.attribute_payload)

        return True

