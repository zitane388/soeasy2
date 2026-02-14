from utils.option_normalizer import (
    normalize_options,
    ensure_option_schema,
    normalize_option_axes_and_variants,
)
from utils.html_cleaner import html_to_text, format_description_blocks
from utils.option_translator import translate_option_groups
import re, hashlib, time


class ProductItem:
    def __init__(self, url):
        self.url = url

        # 고유 item_id
        raw = f"{url}_{time.time()}"
        self.item_id = hashlib.md5(raw.encode()).hexdigest()[:12]
        
        self.checked = True

        # 브랜드/국가
        self.brand = None
        self.country = None

        self.parsed_raw = {}

        # 상세설명 + 번역본
        self.detail_text = ""
        self.final_detail_text = ""
        self.final_detail_html = ""
        self.filtered_detail_text: str | None = None
        
        self.original_name = None
        self.original_ko_name = None
        self.name_keywords = None

        # 상품명/모델명
        self.final_name = None
        self.model_number = None
        
        self.core_id: str | None = None
        self.normalized_tokens: list[str] = []
        
        self.collect_status = "대기"
        self.naver_status = "대기"
        self.windly_status = "대기"
        
        # 가격
        self.base_price = None
        self.base_price_krw = None
        self.price_currency = None

        # 카테고리
        self.category_name = None
        self.category_code = None
        self.matched_category_template_key = None
        
        # 속성
        self.attribute_schema = None
        self.attribute_matched = []
        self.attribute_payload = []

        # 이미지 및 영상
        self.thumbnail_url = None
        self.make_thumbnail_img = None
        
        self.logo_job_results: dict | None = None
        self.final_image_sources: list[str] | None = None
        self.image_checked_map: dict[str, bool] = {}
        
        self.video_url = None
        self.video_file = None
        
        # 썸네일 관련
        self.thumbnail_job = None

        # 사이즈 / 옵션
        self.size_html = ""
        self.options_chart_path = None
        self.size_chart_image_path = None


    def load_data(self, data):

        self.brand = data.get("brand")
        self.country = data.get("country")

        parsed = data.get("parsed", {})

        # =====================================================================
        # 🔥 가격 → 원화 변환
        # =====================================================================
        from utils.currency_utils import COUNTRY_CURRENCY_MAP, get_rate

        country = (self.country or "").lower()
        currency = COUNTRY_CURRENCY_MAP.get(country, "JPY")
        self.price_currency = currency

        prices = parsed.get("prices", {})

        def pick_first_valid(prices_dict):
            for k,v in prices_dict.items():
                if isinstance(v,str) and v.strip():
                    return v
            return None

        raw_price = pick_first_valid(prices)
        self.base_price = raw_price

        def extract_number(v):
            digits = "".join(c for c in v if c.isdigit())
            return int(digits) if digits else None

        price_num = extract_number(raw_price) if raw_price else None

        if price_num:
            krw = int(price_num * get_rate(currency))
            self.base_price_krw = ((krw+9)//10)*10
        else:
            self.base_price_krw = None

        print(f"[PRICE] 원본={raw_price}, KRW={self.base_price_krw}")

        # =====================================================================
        # 🔥 옵션 정규화 + 번역
        # =====================================================================
        parsed = normalize_options(parsed)
        ensure_option_schema(parsed)

        if "options" in parsed:
            parsed["options"] = translate_option_groups(parsed["options"])

        # options 기반 범용 축/조합 구조 보강
        parsed = normalize_option_axes_and_variants(parsed)

        self.parsed_raw = parsed

        self.model_number = parsed.get("model_number")
        self.detail_text  = parsed.get("detail_description")
        
        # ============================================================
        # 상품명 생성 (원문 → 한국어 번역 → 브랜드 자동 prepend)
        # ============================================================
        self.original_name = parsed.get("original_name")

        from utils.utils_translator import translate_to_korean
        from pname_keyword import extract_keywords
        from utils.product_name_generator import generate_final_name
        from utils.brand_canonicalizer import canonicalize_brand

        raw = self.original_name
        self.name_keywords = []
        self.final_name = ""
        if raw:
            try:
                # ① 번역
                ko_name = translate_to_korean(raw)
                # ② 브랜드명 붙이기 (중복 방지)
                lower_name = ko_name.lower()
                if self.brand and self.brand.lower() not in lower_name:
                    self.original_ko_name = f"{self.brand} {ko_name}"
                else:
                    self.original_ko_name = ko_name

                # ③ 키워드 추출
                # Use parser-provided product brand when available.
                raw_keyword_brand = (parsed.get("product_brand") or self.brand or "").strip()
                keyword_brand = canonicalize_brand(
                    raw_keyword_brand,
                    ko_name,
                )
                self.name_keywords = extract_keywords(self.original_ko_name, keyword_brand)

                # ④ LLM 상품명 생성
                self.final_name = generate_final_name(
                    product_item=self,
                    translated_name=self.original_ko_name,
                    keyword_list=self.name_keywords,
                    image_url=None
                )
                if not self.final_name:
                    self.final_name = self.original_ko_name

                # keyword 추출 실패 시 compact 결과로 1회 재수집 후 재생성
                if (not self.name_keywords) and self.final_name:
                    retry_keywords = extract_keywords(self.final_name, keyword_brand)
                    if retry_keywords:
                        print(f"[NAME_RETRY] keywords recollected: {retry_keywords}")
                        self.name_keywords = retry_keywords
                        regenerated = generate_final_name(
                            product_item=self,
                            translated_name=self.final_name,
                            keyword_list=self.name_keywords,
                            image_url=None
                        )
                        if regenerated:
                            self.final_name = regenerated
            except Exception as e:
                print("[상품명 생성 오류]", e)
        

        # =====================================================================
        # LLM 상세설명 자동 생성
        # =====================================================================
        if not self.final_detail_text:
            from llm.llm_detail_generator import generate_sections_from_llm
            llm_html = generate_sections_from_llm(self.detail_text)
            self.final_detail_html = llm_html
            self.final_detail_text = format_description_blocks(html_to_text(llm_html))

        if not self.final_detail_html:
            self.final_detail_html = self.detail_text

        # =====================================================================
        # 대표 이미지
        # =====================================================================
        raw_images = parsed.get("images", [])

        # 원본은 parsed_raw에 그대로 둔다 (절대 수정 금지)
        # 작업용 리스트는 여기서 1회 복사
        self.final_image_sources = list(raw_images) if raw_images else []
        
        self.image_checked_map = {src: False for src in self.final_image_sources}

        # 대표 이미지도 작업용 기준
        self.thumbnail_url = (
            self.final_image_sources[0]
            if self.final_image_sources
            else None
        )
            
        # =====================================================================
        # 영상 URL
        # =====================================================================
        self.video_url = parsed.get("video")

        # =====================================================================
        # 사이즈 표준화 및 PNG 생성
        # =====================================================================
        self.size_headers_original = parsed.get("size_headers_original") or []
        self.size_rows_original = parsed.get("size_rows_original") or []
        self.size_html_raw = parsed.get("size_html_raw") or ""

        from utils.detail_description_generator import normalize_size_chart

        has_chart = (
            self.size_html_raw and
            self.size_headers_original and
            self.size_rows_original
        )

        if has_chart:
            try:
                self.size_html = normalize_size_chart(
                    self.size_headers_original,
                    self.size_rows_original
                )
            except:
                self.size_html = self.size_html_raw


        # =====================================================================
        # 🔥 카테고리 자동 매칭 (자동 적용용)
        # =====================================================================
        from category.matcher.auto_category_pipeline import auto_match_category
        try:
            print("\n====== [LOAD_DATA] AUTO CATEGORY MATCH TRY ======")

            matched = auto_match_category(
                product_name=self.final_name,
                option_names=[
                    v.get("name")
                    for opt in self.parsed_raw.get("options", [])
                    for v in opt.get("values", [])
                    if v.get("name")
                ],
                detail_text=self.final_detail_text,
                image_urls=[self.thumbnail_url] if self.thumbnail_url else [],
            )

            print("[LOAD_DATA] auto_match_category returned =", bool(matched))

            if matched:
                print("[LOAD_DATA] matched.template_key =", matched.get("template_key"))
                print("[LOAD_DATA] matched.category_name =", matched.get("category_name"))
                print("[LOAD_DATA] matched.category_code =", matched.get("category_code"))

                self.category_name = matched.get("category_name")
                self.category_code = matched.get("category_code")
                self.matched_category_template_key = matched.get("template_key")

                print("[LOAD_DATA] category_name SET =", self.category_name)

        except Exception as e:
            print("[AUTO CATEGORY] EXCEPTION:", repr(e))



        print("[load_data] 완료")

        import json

        print("\n================= [ProductItem FINAL STATE] =================")
        print(json.dumps(self.__dict__, ensure_ascii=False, indent=2))
        print("============================================================\n")
