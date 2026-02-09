import os
import tempfile
import requests
from PIL import Image
from utils.path import p

from image_tools.thumb_extensions.pipeline import apply_thumbnail_extensions
from image_tools.thumbnail_engine.pipeline import ThumbnailPipeline
from image_tools.thumbnail_engine.layout.horizontal_slot_layout import HorizontalSlotLayout
from image_tools.thumbnail_engine.layout.overlap_triple_layout import OverlapTripleLayout
from image_tools.thumbnail_engine.layout.overlap_double_layout import OverlapDoubleLayout
from image_tools.image_fetcher import fetch_image_content

from io import BytesIO

def _download_image_to_temp(url: str) -> str:
    try:
        content = fetch_image_content(url)
        if not content:
            raise Exception(f"이미지 데이터를 가져올 수 없습니다: {url[:50]}")

        # 🔥 1. 실제 이미지인지 검증 + 디코딩
        img = Image.open(BytesIO(content)).convert("RGB")

        # 🔥 2. 우리가 통제하는 포맷으로 다시 저장
        fd, path = tempfile.mkstemp(suffix=".jpg")
        with os.fdopen(fd, "wb") as f:
            img.save(f, format="JPEG", quality=95)

        return path

    except Exception as e:
        print(f"[DOWNLOAD_ERROR] {e}")
        return ""



def run_thumbnail_job(job):
    item = job.item
    config = job.config
    output_dir = job.output_dir

    if output_dir and not os.path.isabs(output_dir):
        output_dir = p(output_dir)

    job.mark_running()
    temp_paths = []

    try:
        os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, f"thumbnail_{item.item_id}.png")

        template = config.template
        image_urls = config.image_urls

        pipe = ThumbnailPipeline()
        ok = False

        # ======================================================
        # 1) URL → 로컬 파일
        # ======================================================
        local_paths = []
        for url in image_urls:
            path = _download_image_to_temp(url)
            temp_paths.append(path)
            local_paths.append(path)

        # ======================================================
        # 2) 템플릿별 썸네일 생성
        # ======================================================
        layout_horizontal = HorizontalSlotLayout()
        layout_overlap = OverlapTripleLayout()
        layout_overlap_double = OverlapDoubleLayout()

        if template == "상의 1명":
            img = pipe.build_person_thumbnail(
                image_path=local_paths[0],
                target_type="upper_body",
                canvas_type="square",
                transparent=True,
                force_remove_bg=False,
            )

            final = layout_horizontal.apply(
                images=[img],
                canvas_size=(1000, 1000),
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "하의 1명":
            img = pipe.build_person_thumbnail(
                image_path=local_paths[0],
                target_type="lower_body",
                canvas_type="square",
                transparent=True,
                force_remove_bg=False,
            )

            final = layout_horizontal.apply(
                images=[img],
                canvas_size=(1000, 1000),
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "제품 1개":
            img = pipe.build_product_thumbnail(
                image_path=local_paths[0],
                canvas_type="square",
                transparent=True,
                force_remove_bg=False,
            )

            final = layout_horizontal.apply(
                images=[img],
                canvas_size=(1000, 1000),
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "전신 2명":
            if len(local_paths) < 2:
                raise ValueError("전신 2명 템플릿은 이미지 2개 필요")

            left = pipe.build_person_thumbnail(
                image_path=local_paths[0],
                target_type="full_body",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            right = pipe.build_person_thumbnail(
                image_path=local_paths[1],
                target_type="full_body",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            final = layout_horizontal.apply(
                images=[left, right],
                canvas_size=(1000, 1000),
                to_rgb=True,
            )
            final.save(out_path)
            ok = True
        
        elif template == "상의 2명":
            if len(local_paths) < 2:
                raise ValueError("상의 2명 템플릿은 이미지 2개 필요")

            left = pipe.build_person_thumbnail(
                image_path=local_paths[0],
                target_type="upper_body",
                box_rule_key="upper_body_tight",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            right = pipe.build_person_thumbnail(
                image_path=local_paths[1],
                target_type="upper_body",
                box_rule_key="upper_body_tight",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            final = layout_horizontal.apply(
                images=[left, right],
                canvas_size=(1000, 1000),
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "하의 2명":
            if len(local_paths) < 2:
                raise ValueError("하의 2명 템플릿은 이미지 2개 필요")

            left = pipe.build_person_thumbnail(
                image_path=local_paths[0],
                target_type="lower_body",
                box_rule_key="lower_body_loose",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            right = pipe.build_person_thumbnail(
                image_path=local_paths[1],
                target_type="lower_body",
                box_rule_key="lower_body_loose",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            final = layout_horizontal.apply(
                images=[left, right],
                canvas_size=(1000, 1000),
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        # ===============================
        # ✅ Overlap Triple Product 추가
        # ===============================
        elif template == "제품: 메인1/서브3":
            if len(local_paths) < 4:
                raise ValueError("제품 겹침 3개 템플릿은 이미지 4개 필요")

            main = pipe.build_product_thumbnail(
                image_path=local_paths[0],
                canvas_type="square",
                transparent=True,
                force_remove_bg=True,
            )

            subs = [
                pipe.build_product_thumbnail(
                    image_path=local_paths[i],
                    canvas_type="square",
                    transparent=True,
                    force_remove_bg=True,
                )
                for i in range(1, 4)
            ]

            final = layout_overlap.apply(
                images=[main] + subs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.2,   # 🔑 test_overlap_triple_product와 동일
                to_rgb=True,
            )
            final.save(out_path)
            ok = True
        # ===============================
        # ✅ Overlap Double Product 추가
        # ===============================
        elif template == "제품: 메인1/서브2":
            if len(local_paths) < 3:
                raise ValueError("제품 메인1/서브2 템플릿은 이미지 3개 필요")

            main = pipe.build_product_thumbnail(
                image_path=local_paths[0],
                canvas_type="cavas_700x1000",
                transparent=True,
                force_remove_bg=True,
            )

            subs = [
                pipe.build_product_thumbnail(
                    image_path=local_paths[i],
                    canvas_type="cavas_400x500",
                    transparent=True,
                    force_remove_bg=True,
                )
                for i in range(1, 3)
            ]

            final = layout_overlap_double.apply(
                images=[main] + subs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.3,
                to_rgb=True,
            )
            final.save(out_path)
            ok = True


        else:
            raise ValueError(f"Unknown template: {template}")

        if not ok or not os.path.exists(out_path):
            raise RuntimeError("thumbnail generation failed")

        # ======================================================
        # 3) 확장 후처리 (RGBA 유지)
        # ======================================================
        img = Image.open(out_path).convert("RGBA")
        img = apply_thumbnail_extensions(
            item=item,
            img=img,
            ext_state=config.ext_state,
        )
        img.save(out_path)

        job.mark_done(out_path)
        return True, out_path

    except Exception as e:
        job.mark_failed(e)
        return False, None

    finally:
        # ======================================================
        # 4) 임시 파일 정리
        # ======================================================
        for path in temp_paths:
            try:
                os.remove(path)
            except Exception:
                pass
