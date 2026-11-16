from .box.base import Box
from .box.full_body_box import build_full_body_box
from .box.upper_body_box import build_upper_body_box
from .box.lower_body_box import build_lower_body_box
from .box.product_box import build_product_box
from .logger import get_logger

from .policies import POLICIES
from datetime import datetime

log = get_logger()


class ThumbnailEngine:
    """
    Box / Pivot 계산 전용 Engine (최종)

    ✅ Engine 책임
    - target box 결정
    - pivot 결정
    - canvas_anchor 결정

    ❌ Engine에서 절대 금지
    - scale
    - fill
    - clamp
    - canvas size 계산
    """

    # --------------------------------------------------
    # target box 생성
    # --------------------------------------------------
    def _build_target_box(self, target_type: str, boxes: dict) -> Box:
        if target_type == "full_body":
            return build_full_body_box(
                pose_box=boxes["pose"],
                face_box=boxes.get("face"),
            )

        if target_type == "upper_body":
            return build_upper_body_box(
                upper_body_box=boxes["upper_body"],
                face_box=boxes.get("face"),
                landmarks=boxes.get("landmarks"),
            )

        if target_type == "lower_body":
            return build_lower_body_box(
                lower_body_box=boxes["lower_body"],
            )

        if target_type == "product":
            return build_product_box(
                object_box=boxes["object"],
            )

        raise ValueError(f"Unknown target_type: {target_type}")

    # --------------------------------------------------
    # pivot 계산
    # --------------------------------------------------
    def _get_box_pivot(self, box: Box, mode: str) -> tuple:
        if mode == "top_center":
            return box.top_center
        if mode == "center":
            return box.center
        if mode == "bottom_center":
            return (box.center[0], box.bottom)
        raise ValueError(f"Invalid pivot mode: {mode}")

    # --------------------------------------------------
    # main
    # --------------------------------------------------
    def build(
        self,
        target_type: str,
        boxes: dict,
        canvas_type: str = "square",
        debug_run_id: str | None = None,
    ) -> dict:

        if debug_run_id is None:
            debug_run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        policy = POLICIES[target_type]

        # 1️⃣ box 결정 (절대 수정/확대 없음)
        box = policy["resolve_box"](boxes)

        # 2️⃣ pivot 결정
        pivot = policy["resolve_pivot"](box, boxes)

        # 3️⃣ anchor 결정
        canvas_anchor = policy["canvas_anchor"]

        return {
            "box": box,
            "pivot": pivot,
            "canvas_anchor": canvas_anchor,
            "canvas_type": canvas_type,
            "debug_run_id": debug_run_id,
        }
