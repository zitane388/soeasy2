# image_tools/thumbnail_engine/policies.py

POLICIES = {

    "upper_body": {
        "resolve_box": lambda boxes: boxes["upper_body"],

        "resolve_pivot": lambda box, boxes: (
            box.center[0],
            boxes["face"].y + boxes["face"].h * 0.5
            if boxes.get("face") else box.top
        ),

        "canvas_anchor": "face_mid",

        "engine_scale": False,
        "renderer_scale": True,
    },

    "full_body": {
        "resolve_box": lambda boxes: boxes["pose"],

        # 🔥 상체와 동일한 기준
        "resolve_pivot": lambda box, boxes: (
            box.center[0],
            boxes["face"].y + boxes["face"].h * 0.5
            if boxes.get("face") else box.top
        ),

        # 🔥 top 기준 고정
        "canvas_anchor": "face_mid",

        "engine_scale": False,
        "renderer_scale": True,
    },

    "lower_body": {
        "resolve_box": lambda boxes: boxes["lower_body"],
        "resolve_pivot": lambda box, boxes: box.top_center,
        "canvas_anchor": "top",
        "engine_scale": True,
        "renderer_scale": True,
    },
    
    "lower_body_loose": {
        "resolve_box": lambda boxes: boxes["lower_body"],
        "resolve_pivot": lambda box, boxes: box.top_center,
        "canvas_anchor": "top",
        "engine_scale": True,
        "renderer_scale": True,
    },

    "product": {
        "resolve_box": lambda boxes: boxes["object"],
        "resolve_pivot": lambda box, boxes: box.center,
        "canvas_anchor": "center",
        "engine_scale": True,
        "renderer_scale": True,
    },
}
