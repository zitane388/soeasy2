# models.py

class ProductItem:
    def __init__(self, url):
        self.url = url

        # 브랜드/국가 정보 (파서 매니저에서 들어옴)
        self.brand = None
        self.country = None

        # 파싱 원본 저장
        self.parsed_raw = {}
        self.lens_products = []

        # 상세보기 입력값
        self.final_name = None
        self.final_description = None

        # UI / 출력용
        self.thumbnail_url = None
        self.thumbnail_img = None
        
        self.size_html = ""
        self.size_chart_image = None    


    # --------------------------------------------------------
    # 파싱 결과 + Lens 결과 + 브랜드/국가 저장
    # --------------------------------------------------------
    def load_data(self, data):
        """
        data 구조 예:
        {
            "parsed": {...},
            "lens_products": [...],
            "brand": "uniqlo",
            "country": "jp"
        }
        """

        # 1) 브랜드 / 국가 저장
        self.brand = data.get("brand") or None
        self.country = data.get("country") or None

        # 2) 파싱 원본 저장
        parsed = data.get("parsed", {})
        lens = data.get("lens_products", [])

        self.parsed_raw = parsed
        self.lens_products = lens

        # 3) 썸네일 자동 처리
        images = parsed.get("images", [])
        if images:
            self.thumbnail_url = images[0]

        # 4) 사이즈 HTML
        self.size_html = parsed.get("size_html", "")

        # 5) final_name / final_description 은 UI에서 따로 입력하므로 유지
