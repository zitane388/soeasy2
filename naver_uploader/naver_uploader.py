from naver_uploader.image_uploader import ImageUploader
from naver_uploader.naver_api_client import NaverApiClient
from naver_uploader.builders.naver_product_builder import NaverProductBuilder
from utils.path import p
import os


class NaverUploader:

    def __init__(self):
        self.api = NaverApiClient()
        self.image_uploader = ImageUploader()
        self.builder = NaverProductBuilder()

    # ==============================
    # 단일 상품 업로드
    # ==============================
    def run_for_item(self, item):

        print("\n[NAVER_UPLOADER] run_for_item START")

        rep_uploaded = None
        imgs = item.parsed_raw.get("images", []) or []

        rep_source = None  # "processed" | "url"
        rep_url_used = None

        # 1) 가공 썸네일
        thumb = getattr(item, "make_thumbnail_img", None)
        if thumb:
            if not os.path.isabs(thumb):
                thumb = p(thumb)
            if os.path.exists(thumb):
                print("[IMG] 가공 썸네일 사용:", thumb)
                rep_uploaded = self.image_uploader.upload_image_from_file(thumb)
                rep_source = "processed"

        # 2) thumbnail_url
        if not rep_uploaded and getattr(item, "thumbnail_url", None):
            rep_url_used = item.thumbnail_url
            print("[IMG] 원본 썸네일 URL 사용:", rep_url_used)
            rep_uploaded = self.image_uploader.upload_image_from_url(rep_url_used)
            rep_source = "url"

        # 3) images[0]
        if not rep_uploaded:
            if not imgs:
                print("[WARN] 이미지 없음 → 스킵")
                return False
            rep_url_used = imgs[0]
            print("[IMG] images[0] 사용:", rep_url_used)
            rep_uploaded = self.image_uploader.upload_image_from_url(rep_url_used)
            rep_source = "url"

        if not rep_uploaded:
            print("[ERROR] 대표 이미지 업로드 실패")
            return False

        # ------------------------------
        # 상세 이미지 업로드 범위 결정
        # ------------------------------
        # 대표가 가공썸네일(파일)이면: 상세는 원본 imgs 전체
        # 대표가 원본 URL이면: 상세는 대표로 쓴 URL 제외 (보통 imgs[1:])
        if rep_source == "processed":
            detail_src_urls = imgs
        else:
            # 안전하게 "대표로 사용한 URL"만 제외
            detail_src_urls = [u for u in imgs if u and u != rep_url_used]

        detail_src_urls = detail_src_urls[:9]
        
        detail = []
        for url in detail_src_urls:
            up = self.image_uploader.upload_image_from_url(url)
            if up:
                detail.append(up)

        # payload 생성 (단일 builder)
        body = self.builder.build(
            item,
            detail_images=detail,
            representative_uploaded_url=rep_uploaded,
        )

        # API 전송
        self.api.request(
            "POST",
            "/external/v2/products",
            data=body,
        )

        print("네이버 업로드 완료:", item.final_name)
        return True
