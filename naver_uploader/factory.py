# naver_uploader/factory.py

from naver_uploader.builders.uniqlo.jp_builder import UniqloJpProductBuilder

class BuilderFactory:
    """
    brand + country → builder 자동 선택
    """

    BUILDERS = [
        UniqloJpProductBuilder(),
        # 다음에 US/Global/Muji/Zara 추가 가능
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
