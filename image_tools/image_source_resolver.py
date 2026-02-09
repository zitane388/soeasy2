import os
import logging

log = logging.getLogger(__name__)

def resolve_item_image_sources(item):
    log.debug("[RESOLVE] start")

    # 1) materialize 결과
    final_sources = getattr(item, "final_image_sources", None)
    log.debug(f"[RESOLVE] final_image_sources={type(final_sources)} len={len(final_sources) if isinstance(final_sources, list) else 'N/A'}")

    if isinstance(final_sources, list) and final_sources:
        log.debug("[RESOLVE] -> using final_image_sources")
        return final_sources

    # 2) logo_job_results
    logo_results = getattr(item, "logo_job_results", None)
    log.debug(f"[RESOLVE] logo_job_results type={type(logo_results)}")

    if isinstance(logo_results, list):
        sources = []

        for i, r in enumerate(logo_results):
            log.debug(
                "[RESOLVE] result[%d] "
                "need_remove=%s file_path=%s image=%s url=%s",
                i,
                r.get("need_remove"),
                r.get("file_path"),
                type(r.get("image")),
                r.get("url"),
            )

            p = r.get("file_path")
            if p and isinstance(p, str) and os.path.exists(p):
                log.debug(f"[RESOLVE] -> file_path used: {p}")
                sources.append(p)
                continue

            if r.get("need_remove") and r.get("image") is not None:
                log.debug("[RESOLVE] -> memory image used")
                sources.append(r.get("image"))
                continue

            log.debug("[RESOLVE] -> url used")
            sources.append(r.get("url"))

        log.debug(f"[RESOLVE] sources len={len(sources)}")
        return sources

    # 3) fallback
    parsed = getattr(item, "parsed_raw", {}) or {}
    images = parsed.get("images", [])
    log.debug(f"[RESOLVE] fallback images len={len(images)}")

    return images if isinstance(images, list) else []
