# gui/product_detail/thumb_panel.py

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from gui.widgets.scroll_frame import ScrollFrame
from gui.widgets.thumbnail_helper import load_thumbnail_async
from gui.product_detail.utils import Toast

from image_tools.config import TEMP_IMG_DIR
from image_tools.image_utils import clean_temp_images


class ThumbnailPanel(ttk.LabelFrame):

    def __init__(self, parent, item, owner):
        super().__init__(parent, text="상품 썸네일", padding=10)

        self._ext_state = {}   # 확장 UI 상태 저장
        self.owner = owner
        self.item = item

        self.thumb_slots = []
        self._slot_widgets = []
        self._thumb_img_dict = {}

        self.applied = False
        self.generated_thumb_path = None

        # ⭐ 템플릿 정의 (인스턴스 변수)
        self.template_slots = {
            "상의 1명": ["상의 1명"],
            "하의 1명": ["하의 1명"],
            "전신 2명": ["전신 1명", "전신 1명"],
            "제품 1개": ["제품 1개"],
            "제품: 메인1/서브2": ["메인 1개", "서브 1개", "서브 1개"],
            "제품: 메인1/서브3": ["메인 1개", "서브 1개", "서브 1개", "서브 1개"],
        }


        # ⭐ 드롭다운 표시 변수 (인스턴스 변수)
        self.dropdown_var = tk.StringVar(value="템플릿 선택 ▼")

        self._build_ui()
        self._sync_apply_state_on_open()

    def _sync_apply_state_on_open(self):
        """
        상세보기 열릴 때,
        item.make_thumbnail_img 상태에 따라
        버튼 / preview / applied 상태를 동기화
        """
        path = getattr(self.item, "make_thumbnail_img", None)

        if path and os.path.exists(path):
            self.applied = True
            self.generated_thumb_path = path

            self.apply_btn.config(text="가공 썸네일 해제")
            self._show_final_path(path)
        else:
            self.applied = False
            self.apply_btn.config(text="가공 썸네일 적용")
            self.item.make_thumbnail_img = None
            self._load_initial()


    # ============================================================
    # 템플릿 적용 메서드
    # ============================================================
    def apply_template(self, name):
        name = name.strip()
        if name not in self.template_slots:
            return

        # 버튼 텍스트 변경
        self.dropdown_var.set(f"{name} ▼")

        # 슬롯 생성
        self.thumb_slots = [
            {"role": r, "url": None}
            for r in self.template_slots[name]
        ]

        self._refresh_slots()


    # ============================================================
    # 슬롯 UI 갱신
    # ============================================================
    def _refresh_slots(self):
        for w in self._slot_widgets:
            w.destroy()
        self._slot_widgets.clear()

        slot_parent = self.slot_frame

        for idx, slot in enumerate(self.thumb_slots):
            row = ttk.Frame(slot_parent)
            row.pack(fill="x", pady=2)

            img_lbl = ttk.Label(row, text="[이미지]", width=8)
            img_lbl.pack(side="left")

            url = slot["url"]
            if url and url in self._thumb_img_dict:
                img_lbl.configure(image=self._thumb_img_dict[url], text="")
                img_lbl.image = self._thumb_img_dict[url]

            ttk.Label(row, text=slot["role"]).pack(side="left", padx=(4, 0))

            def rm(i=idx):
                self.thumb_slots[i]["url"] = None
                self._refresh_slots()

            ttk.Button(row, text="X", width=3, command=rm).pack(side="right")

            self._slot_widgets.append(row)
            
    # ============================================================
    # 썸네일 Job 생성 (설정 수집만)
    # ============================================================
    def _build_thumbnail_job(self):
        template = self.dropdown_var.get().replace("▼", "").strip()
        if not template or template == "템플릿 선택":
            return None

        # 슬롯 URL 수집
        image_urls = [s["url"] for s in self.thumb_slots if s.get("url")]
        if not image_urls:
            return None

        # 확장 상태 정리
        resolved_state = {}
        for key, v in self._ext_state.items():
            try:
                # .get() 존재 여부를 더 안전하게 체크
                if hasattr(v, "get"):
                    val = v.get()
                    # BooleanVar인 경우 명시적 bool 변환 (JSON 직렬화 대비)
                    resolved_state[key] = bool(val) if isinstance(v, tk.BooleanVar) else val
                else:
                    resolved_state[key] = v
            except Exception as e:
                print(f"[THUMB_PANEL] Error resolving state for {key}: {e}")
                resolved_state[key] = str(v)

        # config/job 생성
        from models.thumbnail_config import ThumbnailConfig
        from image_tools.thumbnail_job import ThumbnailJob

        config = ThumbnailConfig(
            template=template,
            image_urls=image_urls,
            ext_state=resolved_state,
        )

        job = ThumbnailJob(
            item=self.item,
            config=config,
            output_dir=TEMP_IMG_DIR,
        )

        # ProductItem에는 "참조만"
        self.item.thumbnail_job = job
        return job
    
    def _load_job_to_ui(self):
        job = getattr(self.item, "thumbnail_job", None)
        if not job or not getattr(job, "config", None):
            return

        config = job.config

        # -----------------------------
        # 1) 템플릿 복원
        # -----------------------------
        template = getattr(config, "template", None)
        if template and template in self.template_slots:
            self.dropdown_var.set(f"{template} ▼")
            self.thumb_slots = [
                {"role": r, "url": None}
                for r in self.template_slots[template]
            ]

        # -----------------------------
        # 2) 슬롯 URL 복원
        # -----------------------------
        image_urls = getattr(config, "image_urls", []) or []
        for slot, url in zip(self.thumb_slots, image_urls):
            slot["url"] = url

        # -----------------------------
        # 3) 슬롯 썸네일 이미지 다시 로드 (⭐ 중요)
        # -----------------------------
        root = self.winfo_toplevel()
        THUMB_SIZE = (80, 80)

        def on_loaded(photo, u):
            if photo:
                self._thumb_img_dict[u] = photo
                self._refresh_slots()

        for url in image_urls:
            if url and url not in self._thumb_img_dict:
                load_thumbnail_async(
                    url,
                    THUMB_SIZE,
                    lambda p, u=url: on_loaded(p, u),
                    root
                )

        self._refresh_slots()

        # -----------------------------
        # 4) 확장 UI 상태 복원
        # -----------------------------
        saved_ext_state = getattr(config, "ext_state", {}) or {}

        for key, saved_value in saved_ext_state.items():
            var = self._ext_state.get(key)
            if var and hasattr(var, "set"):
                try:
                    var.set(saved_value)
                except:
                    pass



    # ============================================================
    # UI 구성
    # ============================================================
    def _build_ui(self):
        item = self.item

        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True)

        parent = sf.inner

        # -----------------------------------------------------------
        # 템플릿 선택 버튼
        # -----------------------------------------------------------
        ttk.Button(
            parent,
            textvariable=self.dropdown_var,
            command=self.open_dropdown
        ).pack(fill="x", padx=5, pady=(3, 5))

        # -----------------------------------------------------------
        # 전체 이미지 목록 생성
        # -----------------------------------------------------------
        all_imgs = [
            url for url in item.parsed_raw.get("images", [])
            if isinstance(url, str) and url.startswith("http")
        ]

        # -----------------------------------------------------------
        # 이미지 썸네일 그리드
        # -----------------------------------------------------------
        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=(0, 8))

        THUMB_SIZE = (80, 80)
        COL = 4
        row = col = 0

        root = parent.winfo_toplevel()

        def add_image(url):
            if not self.thumb_slots:
                Toast.show(self, "먼저 템플릿을 선택하세요.", 2000)
                return

            for slot in self.thumb_slots:
                if slot["url"] is None:
                    slot["url"] = url
                    self._refresh_slots()
                    return

            Toast.show(self, "이미지 슬롯이 가득 찼습니다.", 2000)

        for url in all_imgs:
            cell = ttk.Frame(grid)
            cell.grid(row=row, column=col, padx=2, pady=2, sticky="n")

            lb = ttk.Label(cell, text="loading...", width=10)
            lb.pack()

            def on_loaded(photo, u=url, label=lb):
                if photo:
                    self._thumb_img_dict[u] = photo
                    label.config(image=photo, text="")
                    label.image = photo
                else:
                    label.config(text="FAIL")

            load_thumbnail_async(url, THUMB_SIZE, on_loaded, root)

            cell.bind("<Button-1>", lambda e, u=url: add_image(u))
            lb.bind("<Button-1>",   lambda e, u=url: add_image(u))

            col += 1
            if col == COL:
                col = 0
                row += 1
                
        # -----------------------------------------------------------
        # 슬롯 표시 프레임
        # -----------------------------------------------------------
        self.slot_frame = ttk.Frame(parent)
        self.slot_frame.pack(fill="x", padx=5, pady=(0, 8))
        
        
        # -----------------------------------------------------------
        # 확장 UI 자동 로딩
        # -----------------------------------------------------------
        # 1. 확장 UI 스캔 및 빌드 (이때 _ext_state가 채워짐)
        try:
            from gui.product_detail.thumb_panel_extensions.discover import discover_extensions
            exts = discover_extensions(item)
            for ext in exts:
                if "builder" in ext:
                    ext["builder"](self, parent)
        except Exception as e:
            print(f"[THUMB_PANEL] Extension Load Fail: {e}")

        # 2. 확장 UI가 모두 그려진 후에 저장된 Job 데이터를 UI에 복원 (순서 중요!)
        self._load_job_to_ui()

        # 3. 만약 이미 생성된 결과물이 있다면 미리보기 표시
        if self.generated_thumb_path and os.path.exists(self.generated_thumb_path):
            show_big(self.generated_thumb_path)
        
        # -----------------------------------------------------------
        # 생성된 썸네일 미리보기
        # -----------------------------------------------------------
        preview = ttk.Label(parent, text="가공 썸네일 미리보기 영역")
        preview.pack(pady=5)

        def show_big(path):
            img = Image.open(path).resize((250, 250))
            tkimg = ImageTk.PhotoImage(img)
            preview.config(image=tkimg, text="")
            preview.image = tkimg

        # -----------------------------------------------------------
        # 썸네일 생성 버튼
        # -----------------------------------------------------------
        def regen():
            job = self._build_thumbnail_job()
            if not job:
                Toast.show(self, "템플릿/이미지/설정이 부족합니다.", 2000)
                return

            try:
                from image_tools.thumbnail_runner import run_thumbnail_job
                ok, out_path = run_thumbnail_job(job)

                if not ok or not out_path:
                    Toast.show(self, "썸네일 생성 실패", 2000)
                    return

                self.generated_thumb_path = out_path
                show_big(out_path)
                Toast.show(self, "썸네일 생성 완료", 2000)

            except Exception as e:
                print("[THUMB ERROR]", e)
                Toast.show(self, "썸네일 생성 오류", 2000)

            clean_temp_images()


        ttk.Button(parent, text="썸네일 생성", command=regen).pack(pady=5)

        # -----------------------------------------------------------
        # 최종 썸네일 적용/해제
        # -----------------------------------------------------------
        ttk.Label(parent, text="■ 최종 썸네일").pack(anchor="w")

        row2 = ttk.Frame(parent)
        row2.pack(fill="x", pady=(5, 10))

        self.final_preview = ttk.Label(row2, text="로딩 중...", width=30)
        self.final_preview.pack(side="left")

        self.apply_btn = ttk.Button(row2, text="가공 썸네일 적용",
                                    command=self._toggle_apply)
        self.apply_btn.pack(side="right")

        self._load_initial()


    # ============================================================
    # 템플릿 팝업
    # ============================================================
    def open_dropdown(self):

        popup = tk.Toplevel(self)
        popup.title("썸네일 구성 방식 선택")
        popup.geometry("360x320")
        popup.grab_set()

        if not hasattr(self, "_tree_img_cache"):
            self._tree_img_cache = []

        style = ttk.Style(popup)
        style.configure("Treeview", rowheight=70)

        tree = ttk.Treeview(popup, show="tree")
        tree.pack(fill="both", expand=True)

        from gui.widgets.thumbnail_helper import make_square_thumbnail

        def load_icon(filename):
            base = os.path.join(os.path.dirname(__file__), "..", "..", "images")
            path = os.path.abspath(os.path.join(base, filename))

            if not os.path.exists(path):
                print("NO ICON:", path)
                return None

            try:
                im = Image.open(path)
                im = make_square_thumbnail(im, size=(60, 60), pad_color="white")
                img = ImageTk.PhotoImage(im)
                self._tree_img_cache.append(img)
                return img
            except Exception as e:
                print("ICON LOAD FAIL:", e)
                return None

        icon1 = load_icon("thumb01.jpg")
        icon2 = load_icon("thumb02.jpg")
        icon3 = load_icon("thumb03.jpg")
        icon4 = load_icon("thumb04.jpg")
        icon5 = load_icon("thumb05.jpg")
        icon6 = load_icon("thumb06.jpg")

        id1 = tree.insert("", "end", text=" 상의 1명", image=icon1)
        id2 = tree.insert("", "end", text=" 하의 1명", image=icon2)
        id3 = tree.insert("", "end", text=" 전신 2명", image=icon3)
        id4 = tree.insert("", "end", text=" 제품 1개", image=icon4)
        id5 = tree.insert("", "end", text=" 제품: 메인1/서브2", image=icon5)
        id6 = tree.insert("", "end", text=" 제품: 메인1/서브3", image=icon6)

        # -----------------------
        # 클릭 시 선택 강제
        # -----------------------
        def on_click(event):
            row = tree.identify_row(event.y)
            if row:
                tree.selection_set(row)
                tree.focus(row)

        tree.bind("<ButtonRelease-1>", on_click)

        # -----------------------
        # 선택 이벤트
        # -----------------------
        def select(_):
            sel = tree.selection()
            if not sel:
                return
            itemID = sel[0]
            name = tree.item(itemID, "text").strip()

            self.apply_template(name)
            popup.destroy()

        tree.bind("<<TreeviewSelect>>", select)


    # ============================================================
    # 초기 썸네일 로딩
    # ============================================================
    def _load_initial(self):
        label = self.final_preview

        # ---------------------------------------------------------
        # ⭐ 1) 이미 가공된 썸네일이 있을 경우 가장 먼저 표시
        # ---------------------------------------------------------
        if getattr(self.item, "make_thumbnail_img", None):
            path = self.item.make_thumbnail_img
            if os.path.exists(path):
                try:
                    img = Image.open(path)
                    img.thumbnail((140, 140))
                    tkimg = ImageTk.PhotoImage(img)
                    label.config(image=tkimg, text="")
                    label.image = tkimg
                    return
                except:
                    label.config(text="가공 썸네일 표시 실패")
                    return

        # ---------------------------------------------------------
        # ⭐ 2) 가공본 없으면 원본 thumbnail_url 로딩
        # ---------------------------------------------------------
        url = self.item.thumbnail_url
        if not url:
            label.config(text="기본 이미지 없음")
            return

        # ⭐ URL 태깅은 여기서
        label._img_url = url

        root = label.winfo_toplevel()

        def on_loaded(photo, u=url, label=label):
            if not label.winfo_exists():
                return
            if getattr(label, "_img_url", None) != u:
                return

            if photo:
                label.config(image=photo, text="")
                label.image = photo
            else:
                label.config(text="FAIL")

        load_thumbnail_async(url, (140, 140), on_loaded, root)



    # ============================================================
    # 썸네일 적용/해제
    # ============================================================
    def _toggle_apply(self):
        if not self.generated_thumb_path or not os.path.exists(self.generated_thumb_path):
            Toast.show(self, "먼저 썸네일을 생성하세요.", 2000)
            return

        if self.applied:
            self.applied = False
            self.apply_btn.config(text="가공 썸네일 적용")
            self.item.make_thumbnail_img = None
            self._load_initial()
            return

        self.applied = True
        self.apply_btn.config(text="가공 썸네일 해제")
        self.item.make_thumbnail_img = self.generated_thumb_path
        self._show_final_path(self.generated_thumb_path)


    def _show_final_path(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((140, 140))
            tkimg = ImageTk.PhotoImage(img)
            self.final_preview.config(image=tkimg, text="")
            self.final_preview.image = tkimg
        except:
            self.final_preview.config(text="이미지 표시 실패")


    # ============================================================
    # 저장 (통과)
    # ============================================================
    def save(self):
        job = self._build_thumbnail_job()
        if job:
            pass
        return True
