# gui/product_detail/option_panel.py

import tkinter as tk
from tkinter import ttk

from gui.widgets.scroll_frame import ScrollFrame   # ← 핵심 변경
from utils.detail_description_generator import (
    render_options_section,
    html_to_png_options,
)


class OptionPanel(ttk.LabelFrame):

    def __init__(self, parent, item, owner):
        super().__init__(parent, text="옵션", padding=10)
        
        self.owner = owner
        self.item = item

        self.build_ui()

    # --------------------------------------------------------------
    # UI 구성 — 기존 detail_window 옵션 UI 100% 동일
    # --------------------------------------------------------------
    def build_ui(self):
        item = self.item
        parsed = item.parsed_raw
        options = parsed.get("options", [])

        # ============================================================
        # ScrollFrame 도입 (Canvas/Scrollbar 완전 제거)
        # ============================================================
        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True)

        inner = sf.inner  # 기존 self.inner 동일 역할

        # ============================================================
        # 옵션 UI 시작 (원본 detail_window와 완전히 동일)
        # ============================================================

        self.entry_map = {}   # (group_idx, value_idx) → Entry

        if not options:
            ttk.Label(inner, text="옵션 없음").pack(anchor="w", pady=10)

        else:
            from gui.widgets.image_loader import load_image_async

            for gi, group in enumerate(options):
                ttk.Label(inner, text=f"■ {group['group_name']}")\
                    .pack(anchor="w", pady=(10, 4))

                for vi, v in enumerate(group["values"]):
                    row = ttk.Frame(inner)
                    row.pack(anchor="w", pady=4)

                    # 이미지 로드
                    if v.get("image"):
                        lbl = ttk.Label(row, text="로딩중...")
                        lbl.pack(side="left")

                        load_image_async(
                            v["image"], (40, 40),
                            lambda img, lbl=lbl: (
                                lbl.configure(image=img, text="")
                                if img else lbl.configure(text="[오류]"),
                                setattr(lbl, "image", img)
                            ),
                            inner.winfo_toplevel()
                        )

                    # 옵션 이름 Entry
                    e = ttk.Entry(row, width=25)
                    e.insert(0, v["name"])
                    e.pack(side="left", padx=6)

                    self.entry_map[(gi, vi)] = e

        # ============================================================
        # 가격 정보
        # ============================================================
        ttk.Label(inner, text="\n■ 가격 목록").pack(anchor="w", pady=4)

        for cd, price in parsed.get("prices", {}).items():
            ttk.Label(inner,
                      text=f"{cd}: {price}",
                      wraplength=240).pack(anchor="w")

        # ============================================================
        # 가격 상세 표시
        # ============================================================
        price_frame = ttk.Frame(inner)
        price_frame.pack(fill="x", pady=(5, 10))

        raw_price = getattr(item, "base_price", None)
        currency = getattr(item, "price_currency", None)
        price_krw = getattr(item, "base_price_krw", None)

        raw_txt = raw_price if raw_price else "가격 정보 없음"
        cur_txt = f"({currency})" if currency else ""
        krw_txt = f"{price_krw:,}원" if price_krw else "-"

        ttk.Label(price_frame,
                  text=f"대표 가격: {raw_txt} {cur_txt}")\
            .pack(anchor="w")

        ttk.Label(price_frame,
                  text=f"원화 환산: {krw_txt}",
                  foreground="#444")\
            .pack(anchor="w", pady=(2, 0))

        # ============================================================
        # 옵션 저장 버튼
        # ============================================================
        ttk.Button(inner, text="옵션 변경사항 저장",
                   command=self.save)\
            .pack(anchor="w", pady=10)

    # --------------------------------------------------------------
    # 저장 기능 (detail_window의 옵션 저장 기능 그대로)
    # --------------------------------------------------------------
    def save(self):
        item = self.item
        options = item.parsed_raw.get("options", [])

        print("[옵션 저장] Entry 값 → parsed_raw 적용 시작")

        # 옵션명 변경 저장
        for (gi, vi), entry in self.entry_map.items():
            new_val = entry.get().strip()
            old_val = options[gi]["values"][vi]["name"]
            options[gi]["values"][vi]["name"] = new_val
            print(f"[UPDATE] {old_val} → {new_val}")

        # parsed_raw 업데이트
        item.parsed_raw["options"] = options
        
        print("[옵션 저장 완료]")

        return True