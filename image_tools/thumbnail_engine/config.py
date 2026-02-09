# ==========================================================
# Thumbnail Engine Global Config
# 모든 수치·비율·기준점은 여기서만 관리
# ==========================================================


# ----------------------------------------------------------
# 1. 캔버스 프리셋
# ----------------------------------------------------------

CANVAS_PRESETS = {
    "half_vertical": (500, 1000),
    "cavas_700x1000": (700, 1000),
    "cavas_400x500": (400, 500),
    "square": (1000, 1000),
}


# ----------------------------------------------------------
# 2. 타겟 타입 정의
# engine / box / fill 전반에서 공통 사용
# ----------------------------------------------------------

TARGET_TYPES = {
    "full_body",
    "upper_body",
    "lower_body",
    "product",
}


# ----------------------------------------------------------
# 3. MediaPipe 감지 기준 (전신 / 상·하체 판정)
# ----------------------------------------------------------

MEDIAPIPE_CRITERIA = {
    # 전신 판정에 필요한 landmark
    "full_body": {
        "required_landmarks": ["hip", "knee", "ankle"],
    },

    # 상의 판정
    "upper_body": {
        "required_landmarks": ["shoulder"],
        "forbidden_landmarks": ["ankle"],   # 있으면 전신/하체로 빠짐
    },

    # 하의 판정
    "lower_body": {
        "required_landmarks": ["hip", "knee"],
    },
}


# ----------------------------------------------------------
# 4. 얼굴 박스 관련 설정
# ----------------------------------------------------------

FACE_BOX_CONFIG = {
    # 얼굴 상단을 얼마나 잘라낼지 (0.5 = 얼굴 절반 위 제거)
    "crop_top_ratio": 0.5,

    # 얼굴 박스 최소 신뢰 크기 (너무 작으면 무시)
    "min_size_ratio": 0.05,
}


# ----------------------------------------------------------
# 5. 타겟 박스 계산 규칙
# box/*.py 에서 사용
# ----------------------------------------------------------

BOX_RULES = {
    "full_body": {
        "use_face_box": True,
        "use_body_box": True,
        "padding": {
            "top": 0.00,
            "bottom": 0.05,
            "left": 0.0,
            "right": 0.0,
        },
    },

    "upper_body": {
        "use_face_box": True,
        "use_upper_body_box": True,
        "padding": {
            "top": 0.0,      # 얼굴 위 여백 최소
            "bottom": 0.2,    # 상체 아래 여유
            "left": 0.0,
            "right": 0.0,
        },
    },
    
    "upper_body_tight": {
        "use_face_box": True,
        "use_upper_body_box": True,
        "padding": {
            "top": 0.0,      # 얼굴 위 여백 최소
            "bottom": 0.0,    # 상체 아래 여유
            "left": 0.05,
            "right": 0.05,
        },
    },

    "lower_body": {
        "use_lower_body_box": True,
        "padding": {
            "top": 0.1,      # 허리선 위 여유
            "bottom": 0.1,   # 다리 아래 여유
            "left": 0.0,
            "right": 0.0,
        },
    },
    
    "lower_body_loose": {
        "use_lower_body_box": True,
        "padding": {
            "top": 0.2,      # 허리선 위 여유
            "bottom": 0.1,   # 다리 아래 여유
            "left": 0.05,
            "right": 0.05,
        },
    },

    "product": {
        "use_object_box": True,
        "padding": {
            "top": 0.05,
            "bottom": 0.05,
            "left": 0.05,
            "right": 0.05,
        },
    },
}



# ----------------------------------------------------------
# 6. Fill (확대·축소 + 배치) 규칙
# box_pivot: 박스 내부 기준점
# canvas_anchor: 해당 기준점을 캔버스 어디에 둘 것인지
# ----------------------------------------------------------

FILL_RULES = {
    "full_body": {
        "box_pivot": "center",        # center | top_center | bottom_center
        "canvas_anchor": "center",    # top | center | bottom
        "fill_ratio": 0.85,
        "primary_axis": "auto",
    },

    "upper_body": {
        "box_pivot": "top_center",
        "canvas_anchor": "face_mid",
        "fill_ratio": 0.88,
        "primary_axis": "height",
    },

    "lower_body": {
        "box_pivot": "top_center",
        "canvas_anchor": "top",
        "fill_ratio": 0.9,
        "primary_axis": "height",
    },

    "product": {
        "box_pivot": "center",
        "canvas_anchor": "center",
        "fill_ratio": 0.85,
        "primary_axis": "auto",
    },
}



# ----------------------------------------------------------
# 7. Fill 2차 보정 (캔버스 미충족 영역 처리)
# ----------------------------------------------------------

FILL_CANVAS_CONFIG = {
    # 박스 기준 fill 후, 캔버스가 안 찼을 때
    "enable_secondary_fill": True,

    # 2차 확대 최대 허용 비율
    "max_extra_scale": 1.15,
}


# ----------------------------------------------------------
# 8. YOLO 관련 설정
# ----------------------------------------------------------

YOLO_CONFIG = {
    "person_class": "person",
    "product_conf_threshold": 0.4,
}


# ----------------------------------------------------------
# 9. Rembg 설정
# ----------------------------------------------------------

REMBG_CONFIG = {
    "enable": True,
    "post_process": True,
}


# ----------------------------------------------------------
# 10. Layout 기본 설정
# ----------------------------------------------------------

LAYOUT_DEFAULTS = {
    "single": {
        "align": "center",
    },

    "split": {
        "direction": "horizontal",   # horizontal | vertical
        "ratio": 0.5,
    },
}


# ----------------------------------------------------------
# 11. Extension 설정
# ----------------------------------------------------------

EXTENSION_CONFIG = {
    "color_strip": {
        "enable": False,
        "position": "bottom",        # top | bottom | left | right
        "height_ratio": 0.12,
    }
}


# ----------------------------------------------------------
# 12. 디버그 옵션
# ----------------------------------------------------------

DEBUG = {
    "draw_boxes": False,
    "draw_landmarks": False,
    "save_intermediate": False,
}
