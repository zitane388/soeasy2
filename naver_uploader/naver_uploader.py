from naver_uploader.image_uploader import ImageUploader
from naver_uploader.naver_api_client import NaverApiClient

# 유니클로 JP 빌더
from naver_uploader.builders.uniqlo.jp_builder import UniqloJpBuilder

# GU JP 빌더
from naver_uploader.builders.gu.gu_jp_builder import GuJpBuilder


class NaverUploader:

    # brand / country 조합 → 대응 빌더
    BUILDERS = {
        ("유니클로", "jp"): UniqloJpBuilder,
        ("gu", "jp"): GuJpBuilder,        # ★ GU 일본 추가됨
        ("GU", "jp"): GuJpBuilder,        # 혹시 브랜드값이 대문자 GU로 올 경우 대비
    }

    def __init__(self):
        self.api = NaverApiClient()
        self.image_uploader = ImageUploader()

    def _select_builder(self, brand, country):
        cls = self.BUILDERS.get((brand, country))
        if not cls:
            raise Exception(f"Builder 없음: {brand}/{country}")
        return cls()

    def run(self, products):

        for item in products:
            builder = self._select_builder(item.brand, item.country)

            # 1) 대표 이미지 업로드
            rep_url = item.representative_image_url
            rep_uploaded = None

            if rep_url:
                rep_uploaded = self.image_uploader.upload_image_from_url(rep_url)

            if not rep_uploaded:
                print("[WARN] 대표 이미지 업로드 실패 → 건너뜀")
                continue

            # 2) 상세 이미지 업로드
            detail_uploaded = []
            for url in item.parsed_raw.get("images", []):
                if url == rep_url:
                    continue

                up = self.image_uploader.upload_image_from_url(url)
                if up:
                    detail_uploaded.append(up)

            # 3) Builder 호출
            body = builder.build(
                item,
                detail_images=detail_uploaded,
                representative_uploaded_url=rep_uploaded
            )

            # 4) API 등록 요청
            resp = self.api.request(
                "POST",
                "/external/v2/products",
                data=body
            )
            print("등록 완료:", resp)
