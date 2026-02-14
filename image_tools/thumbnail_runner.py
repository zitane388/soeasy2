import os
import tempfile
import requests
from PIL import Image
from utils.path import p

from image_tools.thumb_extensions.pipeline import apply_thumbnail_extensions
from image_tools.thumbnail_engine.pipeline import ThumbnailPipeline
from image_tools.thumbnail_engine.layout.horizontal_slot_layout import HorizontalSlotLayout
from image_tools.thumbnail_engine.layout.overlap_double_horizontal_uniform_layout import OverlapDoubleHorizontalUniformLayout
from image_tools.thumbnail_engine.layout.overlap_quad_horizontal_uniform_layout import OverlapQuadHorizontalUniformLayout
from image_tools.thumbnail_engine.layout.overlap_triple_horizontal_uniform_layout import OverlapTripleHorizontalUniformLayout
from image_tools.thumbnail_engine.layout.overlap_triple_layout import OverlapTripleLayout
from image_tools.thumbnail_engine.layout.overlap_double_layout import OverlapDoubleLayout
from image_tools.image_fetcher import fetch_image_content

from io import BytesIO

def _download_image_to_temp(url: str) -> str:
    try:
        content = fetch_image_content(url)
        if not content:
            raise Exception(f"이미지 데이터를 가져올 수 없습니다: {url[:50]}")

        # 1) 실제 이미지인지 검증하고 디코딩
        img = Image.open(BytesIO(content)).convert("RGB")

        # 2) 우리가 통제하는 포맷(JPEG)으로 재저장
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
        # 1) URL -> 로컬 임시 파일
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
        layout_overlap_double_h_uniform = OverlapDoubleHorizontalUniformLayout()
        layout_overlap_quad_h_uniform = OverlapQuadHorizontalUniformLayout()
        layout_overlap_triple_h_uniform = OverlapTripleHorizontalUniformLayout()
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

        elif template == "전신 3명":
            if len(local_paths) < 3:
                raise ValueError("전신 3명 템플릿은 이미지 3개 필요")

            canvas_size = (1000, 1000)
            canvas_w, canvas_h = canvas_size
            base_w = canvas_w // 3
            slot_w = int(base_w * 1.22)
            overlap = int(base_w * 0.20)
            step = slot_w - overlap
            center_x = canvas_w // 2
            center_slot_x = center_x - (slot_w // 2)

            # 3인 전신 전용: 슬롯 폭을 넓히고 중앙으로 조금 더 모이게 배치
            slots = [
                {"size": (slot_w, canvas_h), "pos": (center_slot_x - step, 0)},
                {"size": (slot_w, canvas_h), "pos": (center_slot_x, 0)},
                {"size": (slot_w, canvas_h), "pos": (center_slot_x + step, 0)},
            ]
            imgs = []
            for i in range(3):
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="full_body",
                    canvas_type="square",
                    box_rule_key="full_body_triple_wide",
                    override_size=slots[i]["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_horizontal.apply(
                images=imgs,
                canvas_size=canvas_size,
                to_rgb=True,
            )
            final.save(out_path)
            ok = True


        elif template == "상의 3명(겹침-균등확장)":
            if len(local_paths) < 3:
                raise ValueError("상의 3명(겹침-균등확장) 템플릿은 이미지 3개 필요")

            slots = layout_overlap_triple_h_uniform.get_slots_info(canvas_size=(1000, 1000), image_count=3)
            try:
                print(f"[THUMB][LAYOUT] template={template} slots={[(s['size'], s['pos']) for s in slots]}")
            except Exception:
                pass
            imgs = []
            # 그리는 순서: left -> right -> center (center가 최상단)
            order = [0, 2, 1]
            for idx, i in enumerate(order):
                slot = slots[idx]
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="upper_body",
                    box_rule_key="upper_body_overlap_uniform",
                    canvas_type="half_vertical",
                    override_size=slot["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_overlap_triple_h_uniform.apply(
                images=imgs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.32,
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "상의 4명(겹침-균등확장)":
            if len(local_paths) < 4:
                raise ValueError("상의 4명(겹침-균등확장) 템플릿은 이미지 4개 필요")

            slots = layout_overlap_quad_h_uniform.get_slots_info(canvas_size=(1000, 1000), image_count=4)
            try:
                print(f"[THUMB][LAYOUT] template={template} slots={[(s['size'], s['pos']) for s in slots]}")
            except Exception:
                pass

            imgs = []
            # paint order: left outer, right outer, left inner, right inner
            # source order remap: L, R, CL, CR
            order = [0, 3, 1, 2]
            for idx, i in enumerate(order):
                slot = slots[idx]
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="upper_body",
                    box_rule_key="upper_body_overlap_uniform",
                    canvas_type="half_vertical",
                    override_size=slot["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_overlap_quad_h_uniform.apply(
                images=imgs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.64,
                outer_inward_ratio=0.26,
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "하의 3명(겹침-균등확장)":
            if len(local_paths) < 3:
                raise ValueError("하의 3명(겹침-균등확장) 템플릿은 이미지 3개 필요")

            slots = layout_overlap_triple_h_uniform.get_slots_info(canvas_size=(1000, 1000), image_count=3)
            try:
                print(f"[THUMB][LAYOUT] template={template} slots={[(s['size'], s['pos']) for s in slots]}")
            except Exception:
                pass
            imgs = []
            # 그리는 순서: left -> right -> center (center가 최상단)
            order = [0, 2, 1]
            for idx, i in enumerate(order):
                slot = slots[idx]
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="lower_body",
                    box_rule_key="lower_body_overlap_uniform",
                    canvas_type="half_vertical",
                    override_size=slot["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_overlap_triple_h_uniform.apply(
                images=imgs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.32,
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        elif template == "하의 4명(겹침-균등확장)":
            if len(local_paths) < 4:
                raise ValueError("하의 4명(겹침-균등확장) 템플릿은 이미지 4개 필요")

            slots = layout_overlap_quad_h_uniform.get_slots_info(canvas_size=(1000, 1000), image_count=4)
            try:
                print(f"[THUMB][LAYOUT] template={template} slots={[(s['size'], s['pos']) for s in slots]}")
            except Exception:
                pass

            imgs = []
            # paint order: left outer, right outer, left inner, right inner
            # source order remap: L, R, CL, CR
            order = [0, 3, 1, 2]
            for idx, i in enumerate(order):
                slot = slots[idx]
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="lower_body",
                    box_rule_key="lower_body_overlap_uniform",
                    canvas_type="half_vertical",
                    override_size=slot["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_overlap_quad_h_uniform.apply(
                images=imgs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.64,
                outer_inward_ratio=0.30,
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
                box_rule_key="upper_body_tight_wide",
                canvas_type="half_vertical",
                transparent=True,
                force_remove_bg=False,
            )

            right = pipe.build_person_thumbnail(
                image_path=local_paths[1],
                target_type="upper_body",
                box_rule_key="upper_body_tight_wide",
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

        elif template == "상의 2명(겹침-균등확장)":
            if len(local_paths) < 2:
                raise ValueError("상의 2명(겹침-균등확장) 템플릿은 이미지 2개 필요")

            slots = layout_overlap_double_h_uniform.get_slots_info(canvas_size=(1000, 1000), image_count=2)
            try:
                print(f"[THUMB][LAYOUT] template={template} slots={[(s['size'], s['pos']) for s in slots]}")
            except Exception:
                pass

            imgs = []
            for i in range(2):
                slot = slots[i]
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="upper_body",
                    box_rule_key="upper_body_overlap_uniform",
                    canvas_type="half_vertical",
                    override_size=slot["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_overlap_double_h_uniform.apply(
                images=imgs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.46,
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

        elif template == "하의 2명(겹침-균등확장)":
            if len(local_paths) < 2:
                raise ValueError("하의 2명(겹침-균등확장) 템플릿은 이미지 2개 필요")

            slots = layout_overlap_double_h_uniform.get_slots_info(canvas_size=(1000, 1000), image_count=2)
            try:
                print(f"[THUMB][LAYOUT] template={template} slots={[(s['size'], s['pos']) for s in slots]}")
            except Exception:
                pass

            imgs = []
            for i in range(2):
                slot = slots[i]
                img = pipe.build_person_thumbnail(
                    image_path=local_paths[i],
                    target_type="lower_body",
                    box_rule_key="lower_body_overlap_uniform",
                    canvas_type="half_vertical",
                    override_size=slot["size"],
                    transparent=True,
                    force_remove_bg=False,
                )
                imgs.append(img)

            final = layout_overlap_double_h_uniform.apply(
                images=imgs,
                canvas_size=(1000, 1000),
                overlap_ratio=0.46,
                to_rgb=True,
            )
            final.save(out_path)
            ok = True

        # ===============================
        # Overlap Triple Product
        # ===============================
        elif template == "제품: 메인1/서브3":
            if len(local_paths) < 4:
                raise ValueError("제품: 메인1/서브3 템플릿은 이미지 4개 필요")

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
                overlap_ratio=0.2,   # test_overlap_triple_product와 동일
                to_rgb=True,
            )
            final.save(out_path)
            ok = True
        # ===============================
        # Overlap Double Product
        # ===============================
        elif template == "제품: 메인1/서브2":
            if len(local_paths) < 3:
                raise ValueError("제품: 메인1/서브2 템플릿은 이미지 3개 필요")

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
