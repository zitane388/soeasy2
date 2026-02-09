# image_tools/logo/logo_job.py

class LogoJob:
    """
    로고 제거 작업 단위 (메모리 기반)

    역할:
    - 작업 상태 관리
    - 이미지별 처리 결과 보관 (메모리)
    - 파일 생성은 하지 않음
    """

    def __init__(self, item, image_urls: list[str]):
        self.item = item
        self.image_urls = image_urls

        # pending | running | done | failed
        self.status: str = "pending"

        # 처리 결과 (list of dict)
        # [
        #   {
        #     "index": int,
        #     "url": str,
        #     "need_remove": bool,
        #     "image": PIL.Image | None,
        #     "file_path": str | None
        #   },
        #   ...
        # ]
        self.results: list[dict] = []

        self.error: str | None = None

    # -------------------------------
    # 상태 전이
    # -------------------------------
    def mark_running(self):
        self.status = "running"
        self.error = None

    def mark_done(self, results: list[dict]):
        self.status = "done"
        self.results = results
        self.error = None

    def mark_failed(self, error):
        self.status = "failed"
        self.results = []
        self.error = str(error)
