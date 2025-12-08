from naver_uploader.image_uploader import ImageUploader
from naver_uploader.naver_api_client import NaverApiClient

# 유니클로/구 일본 빌더
from naver_uploader.builders.uniqlo.jp_builder import UniqloJpBuilder
from naver_uploader.builders.gu.gu_jp_builder import GuJpBuilder


class NaverUploader:

    BUILDERS = {
        ("유니클로", "jp"): UniqloJpBuilder,
        ("gu", "jp"): GuJpBuilder,
        ("GU", "jp"): GuJpBuilder,
    }

    def __init__(self):
        self.api = NaverApiClient()
        self.image_uploader = ImageUploader()

    # ==============================
    # ① 업로드에 사용할 빌더 선택 (필수)
    # ==============================
    def _select_builder(self, brand, country):
        cls = self.BUILDERS.get((brand, country))
        if not cls:
            raise Exception(f"Builder 없음 → {brand}/{country}")
        return cls()

    # ==============================
    # ② 단일 상품 업로드 (run_for_item)
    # ==============================
    def run_for_item(self, item):

        builder = self._select_builder(item.brand, item.country)

        imgs = item.parsed_raw.get("images", [])
        if not imgs:
            print("[WARN] 이미지 없음 → 스킵")
            return False

        # 대표이미지 업로드
        rep_uploaded = self.image_uploader.upload_image_from_url(imgs[0])
        if not rep_uploaded:
            print("[ERROR] 대표 이미지 업로드 실패")
            return False

        # 상세 이미지 업로드
        detail = []
        for url in imgs[1:]:
            up = self.image_uploader.upload_image_from_url(url)
            if up:
                detail.append(up)

        # 빌더 JSON 생성
        body = builder.build(
            item,
            detail_images=detail,
            representative_uploaded_url=rep_uploaded
        )

        # 스마트스토어 API 전송
        resp = self.api.request(
            "POST",
            "/external/v2/products",
            data=body
        )

        print("📌 네이버 업로드 완료:", item.final_name)
        return True  # ← GUI 카운터 갱신용
