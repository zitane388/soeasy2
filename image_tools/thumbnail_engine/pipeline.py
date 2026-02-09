import cv2
from PIL import Image

from .engine import ThumbnailEngine
from .image_renderer import ImageRenderer
from .detection.mediapipe_detector import MediaPipeDetector
from .detection.rembg_detector import RembgDetector
from .target_classifier import auto_classify_target_type
from .logger import get_logger

from .box.upper_body_box import build_upper_body_box
from .box.full_body_box import build_full_body_box
from .box.lower_body_box import build_lower_body_box
from .box.product_box import build_product_box
from .config import CANVAS_PRESETS

log = get_logger()

class ThumbnailPipeline:
    def __init__(self):
        log.info("ThumbnailPipeline init start")
        self.engine = ThumbnailEngine()
        self.renderer = ImageRenderer()
        self.mediapipe = MediaPipeDetector()
        self.rembg = RembgDetector()
        log.info("ThumbnailPipeline init done (mediapipe only)")

    def _resolve_anchor(self, target_type: str | None) -> str:
        if target_type in ("upper_body", "full_body"):
            return "top"
        return "center"

    # --------------------------------------------------
    # 사람 썸네일
    # --------------------------------------------------
    def build_person_thumbnail(
        self,
        image_path: str,
        target_type: str | None,
        override_size: tuple[int, int] = None,
        canvas_type: str = "square",
        transparent: bool = False,
        force_remove_bg: bool = False,
        box_rule_key: str | None = None,
        **kwargs # slot_count 대신 범용적인 kwargs 사용
    ) -> Image.Image:

        log.info(
            "build_person_thumbnail start image=%s target_type=%s override_size=%s",
            image_path, target_type, override_size
        )

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Failed to load image: {image_path}")

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        pose_result = self.mediapipe.detect_pose(img_bgr)
        face_box = self.mediapipe.detect_face_box(img_bgr)

        if not pose_result:
            raise RuntimeError("MediaPipe pose detection failed")

        landmarks = pose_result["landmarks"]

        if target_type is None:
            target_type = auto_classify_target_type(landmarks)

        # 박스 빌드
        pose_box = build_full_body_box(
            pose_box=pose_result["pose"],
            face_box=face_box,
            landmarks=landmarks,
        )
        upper_box = build_upper_body_box(
            upper_body_box=pose_result["upper_body"],
            face_box=face_box,
            landmarks=landmarks,
        )
        lower_box = build_lower_body_box(
            lower_body_box=pose_result["lower_body"]
        )

        boxes = {
            "pose": pose_box,
            "upper_body": upper_box,
            "lower_body": lower_box,
            "face": face_box,
            "landmarks": landmarks,
        }

        engine_result = self.engine.build(
            target_type=target_type,
            boxes=boxes,
            canvas_type=canvas_type,
            box_rule_key=box_rule_key,
        )

        anchor = self._resolve_anchor(target_type)

        # 렌더링 (레이아웃에서 계산되어 넘어온 override_size를 그대로 전달)
        result = self.renderer.render(
            original_image=pil_img,
            box=engine_result["box"],
            pivot=engine_result["pivot"],
            canvas_anchor=anchor,
            canvas_type=canvas_type,
            override_size=override_size,  # 중복 제거 및 단일화
            transparent=transparent,
            force_remove_bg=force_remove_bg,
            debug_run_id=engine_result["debug_run_id"],
            target_type=target_type,
        )

        log.info("build_person_thumbnail done")
        return result

    # --------------------------------------------------
    # 상품 썸네일
    # --------------------------------------------------
    def build_product_thumbnail(
        self,
        image_path: str,
        override_size: tuple[int, int] = None,
        canvas_type: str = "square",
        transparent: bool = False,
        force_remove_bg: bool = False,
        box_rule_key: str | None = None,
        **kwargs
    ) -> Image.Image:

        log.info("build_product_thumbnail start image=%s override_size=%s", image_path, override_size)

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            raise ValueError(f"Failed to load image: {image_path}")

        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)

        object_box = self.rembg.detect_object_box_from_path(image_path)
        if not object_box:
            raise RuntimeError("REMBG failed to detect object box")

        object_box = build_product_box(object_box, box_rule_key)

        engine_result = self.engine.build(
            target_type="product",
            boxes={"object": object_box},
            canvas_type=canvas_type,
            box_rule_key=box_rule_key, 
        )

        result = self.renderer.render(
            original_image=pil_img,
            box=engine_result["box"],
            pivot=engine_result["pivot"],
            canvas_anchor="center",
            canvas_type=canvas_type,
            override_size=override_size, # 전달
            transparent=transparent,
            force_remove_bg=force_remove_bg,
            debug_run_id=engine_result["debug_run_id"],
            target_type="product",
        )

        log.info("build_product_thumbnail done")
        return result