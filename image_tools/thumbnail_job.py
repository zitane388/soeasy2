# image_tools/thumbnail_job_debug.py

class ThumbnailJob:
    def __init__(self, item, config, output_dir):
        self.item = item
        self.config = config
        self.output_dir = output_dir

        self.status = "pending"   # pending | running | done | failed
        self.output_path = None
        self.error = None

        print(f"[JOB INIT] item_id={item.item_id}, template={config.template}, output_dir={output_dir}")

    # ===============================
    # 상태 전이 메서드 (runner가 호출)
    # ===============================
    def mark_running(self):
        self.status = "running"
        self.error = None
        print(f"[JOB RUNNING] item_id={self.item.item_id}")

    def mark_done(self, output_path):
        self.status = "done"
        self.output_path = output_path
        self.error = None
        print(f"[JOB DONE] item_id={self.item.item_id}, output_path={output_path}")

    def mark_failed(self, error):
        self.status = "failed"
        self.output_path = None
        self.error = str(error)
        print(f"[JOB FAILED] item_id={self.item.item_id}, error={error}")
