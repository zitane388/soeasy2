# utils/file_stabilizer.py

import os
import time
import shutil
import uuid

def stabilize_png_file(
    path: str,
    wait_sec: float = 2.0,
    retry: int = 10,
    copy: bool = True
) -> str:
    """
    방금 생성된 PNG 파일을 Windows 기준으로 '안정화'한다.

    동작:
    1) 파일 존재 확인
    2) 여러 번 열기 시도 → 파일 핸들 완전 해제 대기
    3) (선택) 새 파일명으로 복사 → Windows 캐시 우회
    4) 최종적으로 안정화된 파일 경로 반환
    """

    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"[stabilize_png_file] 파일 없음: {path}")

    # --------------------------------------------------
    # 1) 파일 핸들 안정화 대기
    # --------------------------------------------------
    last_err = None
    for _ in range(retry):
        try:
            with open(path, "rb") as f:
                f.read(16)
            last_err = None
            break
        except Exception as e:
            last_err = e
            time.sleep(0.2)

    if last_err:
        raise RuntimeError(
            f"[stabilize_png_file] 파일 핸들 안정화 실패: {path}"
        )

    # --------------------------------------------------
    # 2) 파일 시스템 flush 대기
    # --------------------------------------------------
    time.sleep(wait_sec)

    # --------------------------------------------------
    # 3) 새 파일로 복사 (중요!)
    # --------------------------------------------------
    if copy:
        dir_ = os.path.dirname(path)
        new_name = f"stable_{uuid.uuid4().hex}.png"
        new_path = os.path.join(dir_, new_name)

        shutil.copyfile(path, new_path)

        # 복사본도 한 번 더 안정화
        with open(new_path, "rb") as f:
            f.read(16)

        time.sleep(0.5)

        return new_path

    return path
