import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from gui.widgets.scroll_frame import ScrollFrame
from utils.path import p


MAPPING_PATH = Path(p("templates", "option_mapping.json"))
GROUP_HEADER_BG = "#d9d9d9"


class OptionPanel(ttk.LabelFrame):
    def __init__(self, parent, item, owner):
        super().__init__(parent, text="옵션", padding=10)
        self.owner = owner
        self.item = item
        self.option_mapping = self._load_option_mapping()
        self.build_ui()

    def _normalize_key(self, value: str) -> str:
        return (value or "").strip().lower()

    def _load_option_mapping(self) -> dict[str, str]:
        if not MAPPING_PATH.exists():
            return {}
        try:
            data = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            out: dict[str, str] = {}
            for k, v in data.items():
                if isinstance(k, str) and isinstance(v, str):
                    nk = self._normalize_key(k)
                    nv = v.strip()
                    if nk and nv:
                        out[nk] = nv
            return out
        except Exception:
            return {}

    def _load_raw_mapping_file(self) -> dict[str, str]:
        if not MAPPING_PATH.exists():
            return {}
        try:
            data = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            return {}
        except Exception:
            return {}

    def _save_mapping_pair(self, raw_key: str, mapped_value: str) -> None:
        key = (raw_key or "").strip()
        val = (mapped_value or "").strip()
        if not key or not val:
            messagebox.showwarning("매핑 저장", "원본/결과 값을 모두 입력하세요.", parent=self.winfo_toplevel())
            return

        data = self._load_raw_mapping_file()
        data[key] = val
        MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
        MAPPING_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.option_mapping[self._normalize_key(key)] = val
        messagebox.showinfo("매핑 저장", f"매핑 저장 완료:\n{key} -> {val}", parent=self.winfo_toplevel())

    def _save_group_mapping_from_row(self, gi: int) -> None:
        raw = self.original_group_map.get(gi, "").strip()
        result_entry = self.group_entry_map.get(gi)
        result = result_entry.get().strip() if result_entry else ""
        self._save_mapping_pair(raw, result)
        if result_entry:
            result_entry.configure(style="Mapped.TEntry")

    def _save_option_mapping_from_row(self, gi: int, vi: int) -> None:
        raw = self.original_value_map.get((gi, vi), "").strip()
        result_entry = self.result_entry_map.get((gi, vi))
        result = result_entry.get().strip() if result_entry else ""
        self._save_mapping_pair(raw, result)
        if result_entry:
            result_entry.configure(style="Mapped.TEntry")

    def build_ui(self):
        item = self.item
        parsed = item.parsed_raw
        options = parsed.get("options", [])

        sf = ScrollFrame(self)
        sf.pack(fill="both", expand=True)
        inner = sf.inner

        style = ttk.Style()
        style.configure("Mapped.TEntry", foreground="#111", font=("맑은 고딕", 10, "bold"))
        style.configure("Unmapped.TEntry", foreground="#777", font=("맑은 고딕", 10))
        style.configure("SaveSmall.TButton", padding=(2, 4))

        self.group_entry_map = {}
        self.original_group_map = {}
        self.result_entry_map = {}   # (group_idx, value_idx) -> 결과 Entry
        self.original_value_map = {} # (group_idx, value_idx) -> 원본 문자열

        if not options:
            ttk.Label(inner, text="옵션 없음").pack(anchor="w", pady=10)
        else:
            from gui.widgets.image_loader import load_image_async

            for gi, group in enumerate(options):
                group_row = tk.Frame(inner, bg=GROUP_HEADER_BG)
                group_row.pack(fill="x", pady=(12, 6))
                group_row.grid_columnconfigure(1, weight=1)
                group_row.grid_columnconfigure(2, weight=1)

                tk.Label(
                    group_row,
                    text="그룹명",
                    bg=GROUP_HEADER_BG,
                    font=("맑은 고딕", 10, "bold"),
                ).grid(row=0, column=0, sticky="w", padx=6, pady=6)

                raw_group_name = str(group.get("group_name_original", group.get("group_name", ""))).strip()
                self.original_group_map[gi] = raw_group_name

                g_left = ttk.Entry(group_row, width=24)
                g_left.insert(0, raw_group_name)
                g_left.configure(state="readonly")
                g_left.grid(row=0, column=1, padx=6, pady=6, sticky="ew")

                g_entry = ttk.Entry(group_row, width=24)
                g_entry.insert(0, group.get("group_name", ""))
                g_mapped = bool(self.option_mapping.get(self._normalize_key(raw_group_name)))
                g_entry.configure(style="Mapped.TEntry" if g_mapped else "Unmapped.TEntry")
                g_entry.grid(row=0, column=2, padx=6, pady=6, sticky="ew")
                self.group_entry_map[gi] = g_entry

                ttk.Button(
                    group_row,
                    text="매핑저장",
                    width=8,
                    style="SaveSmall.TButton",
                    command=lambda gi=gi: self._save_group_mapping_from_row(gi),
                ).grid(row=0, column=3, padx=(0, 6), pady=6, sticky="w")

                for vi, value in enumerate(group.get("values", [])):
                    row = ttk.Frame(inner)
                    row.pack(fill="x", pady=4)
                    row.columnconfigure(1, weight=1)
                    row.columnconfigure(2, weight=1)

                    if value.get("image"):
                        lbl = ttk.Label(row, text="로딩중...")
                        lbl.grid(row=0, column=0, sticky="w")
                        load_image_async(
                            value["image"],
                            (40, 40),
                            lambda img, lbl=lbl: (
                                lbl.configure(image=img, text="")
                                if img
                                else lbl.configure(text="[오류]"),
                                setattr(lbl, "image", img),
                            ),
                            inner.winfo_toplevel(),
                        )
                    else:
                        ttk.Label(row, text="").grid(row=0, column=0, sticky="w")

                    raw_name = str(value.get("name_original", value.get("name", ""))).strip()
                    self.original_value_map[(gi, vi)] = raw_name

                    left_original = ttk.Entry(row, width=26)
                    left_original.insert(0, raw_name)
                    left_original.configure(state="readonly")
                    left_original.grid(row=0, column=1, padx=6, sticky="ew")

                    right_result = ttk.Entry(row, width=26)
                    mapped = self.option_mapping.get(self._normalize_key(raw_name), "")
                    right_result.insert(0, mapped or value.get("name", raw_name))
                    right_result.configure(style="Mapped.TEntry" if mapped else "Unmapped.TEntry")
                    right_result.grid(row=0, column=2, padx=6, sticky="ew")
                    self.result_entry_map[(gi, vi)] = right_result

                    ttk.Button(
                        row,
                        text="매핑저장",
                        width=8,
                        style="SaveSmall.TButton",
                        command=lambda gi=gi, vi=vi: self._save_option_mapping_from_row(gi, vi),
                    ).grid(row=0, column=3, sticky="w")

        ttk.Label(inner, text="\n가격 목록").pack(anchor="w", pady=4)
        for code, price in parsed.get("prices", {}).items():
            ttk.Label(inner, text=f"{code}: {price}", wraplength=240).pack(anchor="w")

        price_frame = ttk.Frame(inner)
        price_frame.pack(fill="x", pady=(5, 10))

        raw_price = getattr(item, "base_price", None)
        currency = getattr(item, "price_currency", None)
        price_krw = getattr(item, "base_price_krw", None)

        raw_txt = raw_price if raw_price else "가격정보 없음"
        cur_txt = f"({currency})" if currency else ""
        krw_txt = f"{price_krw:,}원" if price_krw else "-"

        ttk.Label(price_frame, text=f"원본 가격: {raw_txt} {cur_txt}").pack(anchor="w")
        ttk.Label(price_frame, text=f"원화 환산: {krw_txt}", foreground="#444").pack(
            anchor="w", pady=(2, 0)
        )

        ttk.Button(inner, text="옵션 변경사항 저장", command=self.save).pack(
            anchor="w", pady=10
        )

    def save(self):
        item = self.item
        options = item.parsed_raw.get("options", [])

        print("[옵션 저장] 결과 Entry 값 -> parsed_raw 반영 시작")

        for gi, entry in self.group_entry_map.items():
            if gi >= len(options):
                continue
            new_group_name = entry.get().strip()
            old_group_name = options[gi].get("group_name", "")
            options[gi]["group_name"] = new_group_name
            print(f"[UPDATE GROUP] {old_group_name} -> {new_group_name}")

        for (gi, vi), entry in self.result_entry_map.items():
            if gi >= len(options):
                continue
            values = options[gi].get("values", [])
            if vi >= len(values):
                continue
            new_val = entry.get().strip()
            old_val = values[vi].get("name", "")
            values[vi]["name"] = new_val
            print(f"[UPDATE] {old_val} -> {new_val}")

        item.parsed_raw["options"] = options
        print("[옵션 저장 완료]")
        return True
