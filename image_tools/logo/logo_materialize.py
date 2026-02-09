import os
from typing import List

from image_tools.config import TEMP_IMG_DIR
from image_tools.logo.logo_job import LogoJob


def _ensure_item_dir(item_id) -> str:
    """
    item 단위 로고 제거 이미지 저장 디렉토리 확보
    """
    base_dir = os.path.join(TEMP_IMG_DIR, "logo_removed", f"item_{item_id}")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def materialize_logo_job(job: LogoJob) -> List[str]:
    """
    LogoJob 결과를 실제 파일로 materialize 한다.

    규칙:
    - need_remove == False → 원본 URL 그대로 사용
    - need_remove == True  → 메모리 이미지(PIL.Image)를 파일로 저장
    - 파일은 index 기반 고정 이름 사용 (img_{index}.png)
    - 결과 순서는 원본 이미지 순서를 절대 변경하지 않음

    반환:
        URL + 로컬 파일 경로가 섞인 최종 이미지 source 리스트
    """

    if job.status != "done":
        raise RuntimeError(
            f"LogoJob is not done (status={job.status})"
        )

    results = job.results
    if not results:
        return []

    item = job.item
    item_id = getattr(item, "item_id", "unknown")

    item_dir = _ensure_item_dir(item_id)

    final_sources: List[str] = []

    for result in results:
        idx = result.get("index")
        url = result.get("url")
        need_remove = result.get("need_remove", False)

        # --------------------------------------------
        # 1) 로고 제거 필요 없는 경우 → URL 유지
        # --------------------------------------------
        if not need_remove:
            final_sources.append(url)
            continue

        # --------------------------------------------
        # 2) 로고 제거된 이미지 → 파일 생성
        # --------------------------------------------
        img = result.get("image")
        if img is None:
            # 이 경우는 설계상 오류이지만, 시스템은 죽지 않게 한다
            final_sources.append(url)
            continue

        filename = f"img_{idx}.png"
        out_path = os.path.abspath(os.path.join(item_dir, filename))

        # 이미 materialize 된 경우 재사용
        if not os.path.exists(out_path):
            try:
                img.save(out_path, format="PNG")
            except Exception as e:
                # 파일 저장 실패 시에도 시스템은 계속 진행
                final_sources.append(url)
                continue

        # 결과 기록
        result["file_path"] = out_path
        final_sources.append(out_path)

    # --------------------------------------------
    # item 에 최종 결과 귀속
    # --------------------------------------------
    item.final_image_sources = final_sources

    return final_sources
