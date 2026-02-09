# image_tools/logo/logo_runner.py

from image_tools.logo.logo_job import LogoJob


def run_logo_job(job: LogoJob):
    job.mark_running()

    try:
        from image_tools.logo.logo_pipeline import process_logo_images_for_item

        # 🔥 item 말고 job을 넘긴다
        results = process_logo_images_for_item(job)

        job.mark_done(results)
        job.item.logo_job_results = results

        return True, results

    except Exception as e:
        job.mark_failed(e)
        return False, []