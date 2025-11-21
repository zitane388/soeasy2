# naver_uploader/naver_uploader.py

from naver_uploader.image_uploader import ImageUploader
from naver_uploader.naver_api_client import NaverApiClient
from naver_uploader.builders.uniqlo.jp_builder import UniqloJpBuilder


class NaverUploader:

    BUILDERS = {
        ("uniqlo", "jp"): UniqloJpBuilder,
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

            # 이미지 업로드
            imgs = []
            for url in item.parsed_raw.get("images", []):
                u = self.image_uploader.upload_image_from_url(url)
                if u:
                    imgs.append(u)

            if not imgs:
                print("[WARN] 이미지 업로드 실패")
                continue

            body = builder.build(item, imgs)

            # 구매대행 JSON은 product API 다름
            if getattr(item, "purchase_agent", False):
                path = "/external/v2/products"
            else:
                path = "/external/v2/products"

            resp = self.api.request("POST", path, data=body)
            print("등록 완료:", resp)
