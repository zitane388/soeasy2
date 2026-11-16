from .base import register_ui_extension
import tkinter as tk
from tkinter import ttk

@register_ui_extension
def extra_option(item):
    """
    유니클로 + 특정 국가 JP/VN에서 UI 확장 표시
    디버깅 로그를 강화하고 문자열 비교를 더 안전하게 개선함.
    """

    # 1. 브랜드 및 국가 데이터 정규화 (공백 제거, 소문자화)
    brand = str(getattr(item, "brand", "")).strip().lower()
    country = str(getattr(item, "country", "")).strip().lower()

    # [DEBUG] 실행 파일 콘솔에서 확인하기 위한 로그
    print(f"[UI_EXT] Checking condition - Brand: '{brand}', Country: '{country}'")

    # 2. 판정 로직 개선 (한글/영문 및 대소문자 모두 대응)
    is_uniqlo = (brand in ["유니클로", "uniqlo"])
    is_gu = (brand in ["gu", "지유"])
    is_muji = (brand in ["muji", "무인양품"])
    is_allowed_country = (country in ["jp", "vn"])

    allowed = (
        (is_uniqlo and is_allowed_country)
        or (is_gu and country == "jp")
        or (is_muji and country == "jp")
    )

    if not allowed:
        print(f"[UI_EXT] UI not allowed for this item.")
        return None

    print(f"[UI_EXT] Condition met! Preparing builder...")

    def builder(panel, parent):
        """
        실제 UI를 그리는 함수
        """
        print(f"[UI_EXT] Builder is drawing UI components...")
        
        frame = ttk.LabelFrame(parent, text="색상표 확장 옵션")
        frame.pack(fill="x", pady=6, padx=5)

        # ----------------------------------------------------------
        # ✔ 색상표 적용 여부
        # ----------------------------------------------------------
        # 초기값을 True로 설정하여 기본적으로 켜져 있게 함
        var_enable = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(frame, text="색상표 썸네일에 합성", variable=var_enable)
        cb.pack(anchor="w", pady=(5, 5), padx=10)

        # ----------------------------------------------------------
        # ✔ 색상표 위치 선택 (8개 옵션)
        # ----------------------------------------------------------
        pos_var = tk.StringVar(value="h-left-top")

        pos_frame = ttk.LabelFrame(frame, text="합성 위치 설정")
        pos_frame.pack(fill="x", pady=5, padx=5)

        options = [
            ("가로 좌상", "h-left-top"),
            ("가로 우상", "h-right-top"),
            ("가로 좌하", "h-left-bottom"),
            ("가로 우하", "h-right-bottom"),
            ("세로 좌상", "v-left-top"),
            ("세로 우상", "v-right-top"),
            ("세로 좌하", "v-left-bottom"),
            ("세로 우하", "v-right-bottom"),
        ]

        # 2열 격자로 배치
        for i in range(0, len(options), 2):
            row_frame = ttk.Frame(pos_frame)
            row_frame.pack(anchor="w", pady=2)

            for j in range(2):
                if i + j < len(options):
                    label, val = options[i + j]
                    rb = ttk.Radiobutton(row_frame, text=label, variable=pos_var, value=val)
                    rb.pack(side="left", padx=10)

        # [중요] panel의 _ext_state에 변수 객체를 직접 할당
        # 이후 save_all() 등에서 이 객체의 .get()을 호출하여 값을 가져와야 함
        panel._ext_state["color_strip_extra"] = var_enable
        panel._ext_state["color_strip_extra_position"] = pos_var

        print(f"[UI_EXT] UI built and state variables registered.")
        return frame

    return {
        "name": "extra_option",
        "builder": builder
    }