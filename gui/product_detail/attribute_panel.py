# gui/product_detail/attribute_panel.py

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional, Tuple


def _safe_int(x) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None


def _dedup(seq: List[int]) -> List[int]:
    out = []
    seen = set()
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out

def _block_mousewheel(event):
        return "break"

def rebuild_attribute_payload(item) -> None:
    """
    item.attribute_matched -> item.attribute_payload 로 재구성
    SmartStore payload 형식:
      - SELECT: {"categoryAttributeId": ..., "attributeValueSeqs": [...]}
      - TEXT  : {"categoryAttributeId": ..., "attributeValueText": "..."}
    """
    payload = []
    matched = getattr(item, "attribute_matched", []) or []

    for m in matched:
        caid = _safe_int(m.get("categoryAttributeId"))
        if caid is None:
            continue

        seqs = m.get("pickedValueSeqs") or []
        txt = m.get("pickedText")

        if seqs:
            payload.append(
                {
                    "categoryAttributeId": caid,
                    "attributeValueSeqs": _dedup([_safe_int(s) for s in seqs if _safe_int(s) is not None]),
                }
            )
        elif isinstance(txt, str) and txt.strip():
            payload.append(
                {
                    "categoryAttributeId": caid,
                    "attributeValueText": txt.strip(),
                }
            )

    item.attribute_payload = payload


class AttributePanel(ttk.Frame):
    def __init__(
        self,
        parent,
        item,
        *,
        title: str = "■ 속성",
        columns_per_row: int = 10,
    ):
        super().__init__(parent)

        self.item = item
        self.columns_per_row = max(4, int(columns_per_row))

        # 상단 타이틀
        ttk.Label(
            self,
            text=title,
            font=("맑은 고딕", 9)
        ).pack(anchor="w", pady=(0, 8))

        # 내부 컨테이너
        self.body = ttk.Frame(self)
        self.body.pack(fill="x", expand=True)

        self._vars = []
        self._widgets = []
        self._multi_vars = {}
        self._rendered_once = False

        self._ensure_item_fields()

        if getattr(self.item, "attribute_schema", None):
            self.render()
        else:
            self._render_empty()

    def _render_empty(self):
        for w in self.body.winfo_children():
            w.destroy()
        ttk.Label(self.body, text="카테고리 속성 스키마가 없습니다.").pack(anchor="w")
        self._rendered_once = False

    # ------------------------------------------------------------
    # Public
    # ------------------------------------------------------------
    def rebuild(self):
        for w in self.body.winfo_children():
            w.destroy()
        self._vars.clear()
        self._widgets.clear()
        self._multi_vars.clear()
        self._ensure_item_fields()
        self.render()


    def set_schema(self, schema_raw: List[Dict[str, Any]]):
        import copy
        # ✅ 외부에서 schema_raw를 in-place로 만져도 UI는 영향 안 받게 차단
        self.item.attribute_schema = copy.deepcopy(schema_raw or [])
        self.rebuild()


    def set_matched(self, matched: List[Dict[str, Any]]):
        self.item.attribute_matched = matched or []
        rebuild_attribute_payload(self.item)
        self.rebuild()

    # ------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------
    def _ensure_item_fields(self):
        # 없으면 생성 (OK)
        if not hasattr(self.item, "attribute_schema"):
            self.item.attribute_schema = None
        if not hasattr(self.item, "attribute_matched"):
            self.item.attribute_matched = []
        if not hasattr(self.item, "attribute_payload"):
            self.item.attribute_payload = []

        # None이면 그대로 둔다 (중요)
        if self.item.attribute_matched is None:
            self.item.attribute_matched = []
        if self.item.attribute_payload is None:
            self.item.attribute_payload = []


    def _get_entry_by_caid(self, caid: int) -> Optional[Dict[str, Any]]:
        schema = getattr(self.item, "attribute_schema", []) or []
        for en in schema:
            a = (en.get("attribute") or {})
            name = a.get("attributeName")
            ctype = a.get("attributeClassificationType")
            vals = a.get("attributeValues") or []
            if name in ("주요소재", "패턴", "기능", "종류"):
                print(f"[UI_SCHEMA] {name} {ctype} values={len(vals)}")
            try:
                cid = _safe_int(
                    (en.get("id") or {}).get("categoryAttributeId")
                    or en.get("categoryAttributeId")
                )
                if cid == caid:
                    return en
            except Exception:
                continue
        return None

    def _get_attr_meta(self, entry: Dict[str, Any]) -> Tuple[int, str, str, bool, List[Dict[str, Any]]]:
        id_obj = entry.get("id") or {}
        attr = entry.get("attribute") or {}

        caid = _safe_int(id_obj.get("categoryAttributeId")) or -1
        name = str(attr.get("attributeName") or "").strip()
        ctype = str(attr.get("attributeClassificationType") or "").strip()
        required = bool(entry.get("attributeRequired"))
        values = attr.get("attributeValues") or []
        if not isinstance(values, list):
            values = []
        return caid, name, ctype, required, values

    def _find_matched(self, caid: int) -> Optional[Dict[str, Any]]:
        for m in getattr(self.item, "attribute_matched", []) or []:
            if _safe_int(m.get("categoryAttributeId")) == caid:
                return m
        return None

    def _is_checked(self, caid: int, seq: int) -> bool:
        m = self._find_matched(caid)
        if not m:
            return False
        return seq in (m.get("pickedValueSeqs") or [])

    def _set_matched_row(self, caid: int, seqs: Optional[List[int]] = None, text: Optional[str] = None):
        matched = getattr(self.item, "attribute_matched", []) or []
        # remove existing
        matched = [m for m in matched if _safe_int(m.get("categoryAttributeId")) != caid]

        seqs = seqs or []
        seqs = _dedup([_safe_int(s) for s in seqs if _safe_int(s) is not None])

        row = {
            "categoryAttributeId": caid,
            "pickedValueSeqs": seqs,
            "pickedText": (text.strip() if isinstance(text, str) and text.strip() else None),
        }

        # keep only if has something
        if row["pickedValueSeqs"] or row["pickedText"]:
            matched.append(row)

        self.item.attribute_matched = matched
        rebuild_attribute_payload(self.item)

    def _clear_attr(self, caid: int):
        matched = getattr(self.item, "attribute_matched", []) or []
        matched = [m for m in matched if _safe_int(m.get("categoryAttributeId")) != caid]
        self.item.attribute_matched = matched
        rebuild_attribute_payload(self.item)

    # ------------------------------------------------------------
    # Render
    # ------------------------------------------------------------
    def render(self):
        schema = getattr(self.item, "attribute_schema", []) or []
        if not schema:
            ttk.Label(self.body, text="카테고리 속성 스키마가 없습니다.").pack(anchor="w")
            return

        groups: Dict[str, List[Dict[str, Any]]] = {}
        for entry in schema:
            group = entry.get("categoryAttributeGroup") or {}
            gname = str(group.get("attributeGroupName") or "기본").strip()
            groups.setdefault(gname, []).append(entry)

        for gname in sorted(groups.keys()):
            group_frame = ttk.Frame(self.body)
            group_frame.pack(fill="x", expand=True, pady=(6, 10))

            ttk.Label(
                group_frame,
                text=gname,
                font=("맑은 고딕", 10, "bold")
            ).pack(anchor="w", pady=(0, 4))

            content = ttk.Frame(group_frame)
            content.pack(fill="x", expand=True)

            entries = groups[gname]
            entries.sort(key=lambda en: (
                0 if en.get("attributeRequired") else 1,
                (en.get("attribute") or {}).get("attributeName", "")
            ))

            for en in entries:
                caid, name, ctype, required, values = self._get_attr_meta(en)
                if caid < 0 or not name:
                    continue

                row = ttk.Frame(content)
                row.pack(fill="x", expand=True, pady=3)

                label = name + (" (필수)" if required else "")
                ttk.Label(
                    row,
                    text=label,
                    width=16,
                    anchor="w"
                ).pack(side="left", padx=(0, 8))

                right = ttk.Frame(row)
                right.pack(side="left", fill="x", expand=True)

                if ctype == "MULTI_SELECT":
                    self._render_multi_select(right, caid, values)
                elif ctype == "SINGLE_SELECT":
                    self._render_single_select(right, caid, values)
                elif ctype == "TEXT":
                    self._render_text(right, caid)
                    
        self._rendered_once = True


    def _render_multi_select(self, parent, caid, values):
        # 1. highlightthickness를 0으로 해서 불필요한 테두리 공간 제거
        canvas = tk.Canvas(parent, highlightthickness=0)
        canvas.pack(fill="x", anchor="nw") # expand=True를 제거하여 불필요한 확장을 막음

        inner = ttk.Frame(canvas)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def sync(event=None):
            # 내부 콘텐츠(inner)가 요청하는 실제 높이를 가져옵니다.
            inner_height = inner.winfo_reqheight()
            inner_width = canvas.winfo_width()
            
            # 2. 캔버스의 높이를 내부 프레임 높이와 동일하게 설정 (핵심!)
            canvas.configure(height=inner_height)
            
            # 3. 내부 윈도우 너비를 캔버스에 맞춤
            canvas.itemconfigure(win, width=inner_width)
            canvas.configure(scrollregion=(0, 0, inner_width, inner_height))

        # Canvas와 inner 프레임 모두 크기 변화를 감지하도록 바인딩
        canvas.bind("<Configure>", sync)
        inner.bind("<Configure>", sync)

        # -------------------------
        # 값 분배 (Grid 방식 권장)
        # -------------------------
        COLS = 2
        inner.columnconfigure(list(range(COLS)), weight=1)

        for idx, v in enumerate(values):
            seq = _safe_int(v.get("attributeValueSeq"))
            txt = (v.get("attributeValueText") or v.get("attributeValueName") or "").strip()
            if not seq or not txt: continue

            var = tk.BooleanVar(value=self._is_checked(caid, seq))
            self._vars.append(var)
            self._multi_vars.setdefault(caid, []).append(var)

            cb = ttk.Checkbutton(
                inner,
                text=txt,
                variable=var,
                command=lambda s=seq, vv=var: self._update_multi_select(caid, s, vv.get())
            )
            cb.grid(row=idx // COLS, column=idx % COLS, sticky="w", padx=5, pady=2)

        # 초기 렌더링 시 높이 계산 강제 실행
        inner.update_idletasks()
        sync()


    def _update_multi_select(self, caid: int, seq: int, checked: bool):
        m = self._find_matched(caid)
        if not m:
            if checked:
                self._set_matched_row(caid, seqs=[seq], text=None)
            return

        seqs = m.get("pickedValueSeqs") or []
        seqs = [_safe_int(s) for s in seqs if _safe_int(s) is not None]

        if checked and seq not in seqs:
            seqs.append(seq)
        elif (not checked) and seq in seqs:
            seqs.remove(seq)

        if not seqs:
            self._clear_attr(caid)
        else:
            self._set_matched_row(caid, seqs=seqs, text=None)

    
    
    def _render_single_select(self, parent, caid: int, values: List[Dict[str, Any]]):
        # value 목록
        items: List[Tuple[str, int]] = []
        for v in values:
            seq = _safe_int(v.get("attributeValueSeq"))
            txt = (
                v.get("attributeValueText")
                or v.get("attributeValueName")
                or str(v.get("minAttributeValue") or "")
            ).strip()
            if seq is None or not txt:
                continue
            items.append((txt, seq))

        # 현재 선택
        cur_label = "선택"
        m = self._find_matched(caid)
        cur_seq = None
        if m and (m.get("pickedValueSeqs") or []):
            cur_seq = _safe_int(m["pickedValueSeqs"][0])
            if cur_seq is not None:
                for t, s in items:
                    if s == cur_seq:
                        cur_label = t
                        break

        row = ttk.Frame(parent)
        row.pack(fill="x", expand=True)

        labels = ["선택"] + [t for t, _ in items]

        combo = ttk.Combobox(row, values=labels, state="readonly")
        combo.set(cur_label)
        combo.pack(side="left", fill="x", expand=True)
        
        combo.bind("<MouseWheel>", _block_mousewheel)      # Windows
        combo.bind("<Button-4>", _block_mousewheel)        # Linux (wheel up)
        combo.bind("<Button-5>", _block_mousewheel)        # Linux (wheel down)
        combo.bind("<Shift-MouseWheel>", _block_mousewheel)

        def on_select(_evt=None):
            selected = combo.get()
            if selected == "선택":
                self._clear_attr(caid)
                return

            seq = None
            for t, s in items:
                if t == selected:
                    seq = s
                    break
            if seq is None:
                self._clear_attr(caid)
                return

            self._set_matched_row(caid, seqs=[seq], text=None)

        combo.bind("<<ComboboxSelected>>", on_select)

    def _render_text(self, parent, caid: int):
        row = ttk.Frame(parent)
        row.pack(fill="x", expand=True)

        m = self._find_matched(caid)
        cur = ""
        if m and isinstance(m.get("pickedText"), str):
            cur = m["pickedText"].strip()

        var = tk.StringVar(value=cur)
        self._vars.append(var)

        entry = ttk.Entry(row, textvariable=var)
        entry.pack(side="left", fill="x", expand=True)

        def on_commit(_evt=None):
            txt = var.get()
            if not isinstance(txt, str) or not txt.strip():
                self._clear_attr(caid)
            else:
                self._set_matched_row(caid, seqs=[], text=txt.strip())

        # 엔터 / 포커스 아웃 시 자동 반영
        entry.bind("<Return>", on_commit)
        entry.bind("<FocusOut>", on_commit)
    
    # ------------------------------------------------------------
    # Public: 현재 UI 상태를 item에 확정 반영
    # ------------------------------------------------------------
    def collect_current_values(self):
        """
        현재 UI 상태를 기준으로
        item.attribute_matched / attribute_payload를 확정한다.

        현재 구조에서는 대부분 실시간 반영이므로
        '보장(sync)' 목적의 메서드이다.
        """
        # 혹시 남아 있을 수 있는 Entry 포커스 강제 커밋
        for w in self.body.winfo_children():
            try:
                w.focus_force()
            except Exception:
                pass

        # 최종 payload 재구성 (안전)
        rebuild_attribute_payload(self.item)

        return {
            "matched": self.item.attribute_matched,
            "payload": self.item.attribute_payload,
        }

