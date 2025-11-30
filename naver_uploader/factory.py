# naver_uploader/factory.py

from naver_uploader.builders.uniqlo.jp_builder import UniqloJpBuilder
from naver_uploader.builders.gu.gu_jp_builder import GuJpBuilder


class BuilderFactory:
    """
    brand + country → builder 자동 선택
    """

    BUILDERS = [
        UniqloJpBuilder(),   # 기존 유니클로
        GuJpBuilder(),              # ★ 신규 GU 일본 빌더 추가
    ]

    @staticmethod
    def get_builder(brand, country):
        """
        (brand, country)에 맞는 builder instance 반환
        """

        for builder in BuilderFactory.BUILDERS:
            if builder.matches(brand, country):
                return builder

        raise ValueError(f"[BuilderFactory] Builder 없음 → brand={brand}, country={country}")
