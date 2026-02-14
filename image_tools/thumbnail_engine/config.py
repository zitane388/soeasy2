# ==========================================================
# Thumbnail Engine Global Config
# 紐⑤뱺 ?섏튂쨌鍮꾩쑉쨌湲곗??먯? ?ш린?쒕쭔 愿由?
# ==========================================================


# ----------------------------------------------------------
# 1. 罹붾쾭???꾨━??
# ----------------------------------------------------------

CANVAS_PRESETS = {
    "half_vertical": (500, 1000),
    "cavas_700x1000": (700, 1000),
    "cavas_400x500": (400, 500),
    "square": (1000, 1000),
}


# ----------------------------------------------------------
# 2. ?寃?????뺤쓽
# engine / box / fill ?꾨컲?먯꽌 怨듯넻 ?ъ슜
# ----------------------------------------------------------

TARGET_TYPES = {
    "full_body",
    "upper_body",
    "lower_body",
    "product",
}


# ----------------------------------------------------------
# 3. MediaPipe 媛먯? 湲곗? (?꾩떊 / ?겶룻븯泥??먯젙)
# ----------------------------------------------------------

MEDIAPIPE_CRITERIA = {
    # ?꾩떊 ?먯젙???꾩슂??landmark
    "full_body": {
        "required_landmarks": ["hip", "knee", "ankle"],
    },

    # ?곸쓽 ?먯젙
    "upper_body": {
        "required_landmarks": ["shoulder"],
        "forbidden_landmarks": ["ankle"],   # ?덉쑝硫??꾩떊/?섏껜濡?鍮좎쭚
    },

    # ?섏쓽 ?먯젙
    "lower_body": {
        "required_landmarks": ["hip", "knee"],
    },
}


# ----------------------------------------------------------
# 4. ?쇨뎬 諛뺤뒪 愿???ㅼ젙
# ----------------------------------------------------------

FACE_BOX_CONFIG = {
    # ?쇨뎬 ?곷떒???쇰쭏???섎씪?쇱? (0.5 = ?쇨뎬 ?덈컲 ???쒓굅)
    "crop_top_ratio": 0.5,

    # ?쇨뎬 諛뺤뒪 理쒖냼 ?좊ː ?ш린 (?덈Т ?묒쑝硫?臾댁떆)
    "min_size_ratio": 0.05,
}


# ----------------------------------------------------------
# 5. ?寃?諛뺤뒪 怨꾩궛 洹쒖튃
# box/*.py ?먯꽌 ?ъ슜
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

    "full_body_triple_wide": {
        "use_face_box": True,
        "use_body_box": True,
        "padding": {
            "top": 0.02,
            "bottom": 0.08,
            "left": 0.08,
            "right": 0.08,
        },
    },

    "upper_body": {
        "use_face_box": True,
        "use_upper_body_box": True,
        "padding": {
            "top": 0.0,      # ?쇨뎬 ???щ갚 理쒖냼
            "bottom": 0.2,    # ?곸껜 ?꾨옒 ?ъ쑀
            "left": 0.0,
            "right": 0.0,
        },
    },
    
    "upper_body_tight": {
        "use_face_box": True,
        "use_upper_body_box": True,
        "padding": {
            "top": 0.0,      # ?쇨뎬 ???щ갚 理쒖냼
            "bottom": 0.0,    # ?곸껜 ?꾨옒 ?ъ쑀
            "left": 0.05,
            "right": 0.05,
        },
    },


    "upper_body_tight_wide": {
        "use_face_box": True,
        "use_upper_body_box": True,
        "padding": {
            "top": 0.0,
            "bottom": 0.0,
            "left": 0.10,
            "right": 0.10,
        },
    },

    "upper_body_overlap_uniform": {
        "use_face_box": True,
        "use_upper_body_box": True,
        "padding": {
            "top": 0.0,
            "bottom": 0.0,
            "left": 0.16,
            "right": 0.16,
        },
    },

    "lower_body": {
        "use_lower_body_box": True,
        "padding": {
            "top": 0.1,      # ?덈━?????ъ쑀
            "bottom": 0.1,   # ?ㅻ━ ?꾨옒 ?ъ쑀
            "left": 0.0,
            "right": 0.0,
        },
    },
    
    "lower_body_loose": {
        "use_lower_body_box": True,
        "padding": {
            "top": 0.2,      # ?덈━?????ъ쑀
            "bottom": 0.1,   # ?ㅻ━ ?꾨옒 ?ъ쑀
            "left": 0.05,
            "right": 0.05,
        },
    },

    "lower_body_overlap_uniform": {
        "use_lower_body_box": True,
        "padding": {
            "top": 0.2,
            "bottom": 0.1,
            "left": 0.16,
            "right": 0.16,
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
# 6. Fill (?뺣?쨌異뺤냼 + 諛곗튂) 洹쒖튃
# box_pivot: 諛뺤뒪 ?대? 湲곗???
# canvas_anchor: ?대떦 湲곗??먯쓣 罹붾쾭???대뵒????寃껋씤吏
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
# 7. Fill 2李?蹂댁젙 (罹붾쾭??誘몄땐議??곸뿭 泥섎━)
# ----------------------------------------------------------

FILL_CANVAS_CONFIG = {
    # 諛뺤뒪 湲곗? fill ?? 罹붾쾭?ㅺ? ??李쇱쓣 ??
    "enable_secondary_fill": True,

    # 2李??뺣? 理쒕? ?덉슜 鍮꾩쑉
    "max_extra_scale": 1.15,
}


# ----------------------------------------------------------
# 8. YOLO 愿???ㅼ젙
# ----------------------------------------------------------

YOLO_CONFIG = {
    "person_class": "person",
    "product_conf_threshold": 0.4,
}


# ----------------------------------------------------------
# 9. Rembg ?ㅼ젙
# ----------------------------------------------------------

REMBG_CONFIG = {
    "enable": True,
    "post_process": True,
}


# ----------------------------------------------------------
# 10. Layout 湲곕낯 ?ㅼ젙
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
# 11. Extension ?ㅼ젙
# ----------------------------------------------------------

EXTENSION_CONFIG = {
    "color_strip": {
        "enable": False,
        "position": "bottom",        # top | bottom | left | right
        "height_ratio": 0.12,
    }
}


# ----------------------------------------------------------
# 12. ?붾쾭洹??듭뀡
# ----------------------------------------------------------

DEBUG = {
    "draw_boxes": False,
    "draw_landmarks": False,
    "save_intermediate": False,
}

