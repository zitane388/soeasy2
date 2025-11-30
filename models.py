# models.py

from utils.option_normalizer import normalize_options, ensure_option_schema
from utils.html_cleaner import html_to_text, format_description_blocks
from utils.option_translator import translate_option_groups
import re
import hashlib, time


class ProductItem:
    def __init__(self, url):
        self.url = url

        # ------------------------------------------------
        # 🔥 Windly용 고유 item_id 생성
        # ------------------------------------------------
        raw = f"{url}_{time.time()}"
        self.item_id = hashlib.md5(raw.encode()).hexdigest()[:12]

        # 브랜드/국가
        self.brand = None
        self.country = None

        # 파싱 원본
        self.parsed_raw = {}
        self.lens_products = []

        # 상세설명 구조
        self.detail_html = ""          # HTML 원본
        self.detail_text = ""          # 텍스트 버전

        self.final_detail_text = ""    # UI에서 수정한 텍스트
        self.final_detail_html = ""    # 네이버 업로드용 HTML 변환본

        self.final_name = None
        self.representative_image_url = None
        self.model_number = None
        
        self.base_price = None        # 원래 가격 (통화 문자 포함)
        self.base_price_krw = None    # 환율 적용된 KRW 가격 (int)
        self.price_currency = None
        
        self.category_name = None
        self.category_code = None

        # 이미지/썸네일
        self.thumbnail_url = None
        self.thumbnail_img = None
        
        self.video_url = None
        self.video_file = None

        # 사이즈표(HTML만)
        self.size_html = ""

        self.options_chart_path = None
        self.size_chart_image_path = None

    # --------------------------------------------------------
    # 개선된 load_data()
    # --------------------------------------------------------
    def load_data(self, data):

        self.brand = data.get("brand")
        self.country = data.get("country")

        parsed = data.get("parsed", {})
        self.lens_products = data.get("lens_products", [])
        
        self.video_url = parsed.get("video") or None

        # ============================================================
        # 🔥 국가 기반 통화 설정 + 원화 가격 계산
        # ============================================================
        from utils.currency_utils import COUNTRY_CURRENCY_MAP, get_rate

        country = (self.country or "").lower()
        currency = COUNTRY_CURRENCY_MAP.get(country, "JPY")
        self.price_currency = currency

        prices = parsed.get("prices", {})

        def pick_first_valid(prices_dict):
            for k in prices_dict:
                v = prices_dict[k]
                if isinstance(v, str) and v.strip():
                    return v
            return None

        raw_price = pick_first_valid(prices)
        self.base_price = raw_price

        def extract_number(p):
            digits = "".join([c for c in p if c.isdigit()])
            return int(digits) if digits else None

        price_num = extract_number(raw_price) if raw_price else None

        if price_num:
            rate = get_rate(currency)
            krw_price = int(price_num * rate)
            rounded = ((krw_price + 9) // 10) * 10
            self.base_price_krw = rounded
        else:
            self.base_price_krw = None

        print(f"[PRICE] 대표가격 = {raw_price}")
        print(f"[PRICE] 원화가격 = {self.base_price_krw}")

        # ============================================================
        # 🔥 옵션 구조 표준화 + 번역
        # ============================================================
        parsed = normalize_options(parsed)
        ensure_option_schema(parsed)

        print("\n[load_data] 옵션 표준화 후 구조 확인:")
        print(parsed.get("options"))

        if "options" in parsed:
            print("[load_data] 옵션 번역 시작")
            parsed["options"] = translate_option_groups(parsed["options"])
            print("[load_data] 옵션 번역 완료")
            print(parsed["options"])

        self.parsed_raw = parsed

        # =============================
        # 상세설명 텍스트 원본 설정
        # =============================
        original_text = parsed.get("detail_description", "")
        self.detail_text = original_text
        cleaned_text = original_text

        # 🔥 모델번호 제거
        import re
        model_pattern = r"商品番号[:：]?\s*([0-9A-Za-z\-]+)"
        m = re.search(model_pattern, cleaned_text)
        if m:
            self.model_number = m.group(1)
            cleaned_text = re.sub(model_pattern, "", cleaned_text).strip()

        self.detail_text = cleaned_text

        # ============================================================
        # 🔥 LLM 상세설명 자동 생성
        # ============================================================
        if not self.final_detail_text or self.final_detail_text == original_text:
            if original_text.strip():
                from llm.llm_detail_generator import generate_sections_from_llm
                print("[LLM] 상세설명 번역 생성:", self.url)

                llm_html = generate_sections_from_llm(original_text)
                self.final_detail_html = llm_html
                text_raw = html_to_text(llm_html)
                self.final_detail_text = format_description_blocks(text_raw)

        if not self.final_detail_html:
            self.final_detail_html = self.detail_text

        # ============================================================
        # 🔥 대표 이미지 설정
        # ============================================================
        imgs = parsed.get("images", [])
        if imgs:
            self.thumbnail_url = imgs[0]
            self.representative_image_url = imgs[0]

        # ============================================================
        # 🔥 사이즈표 데이터 로딩
        # ============================================================
        self.size_headers_original = parsed.get("size_headers_original") or []
        self.size_rows_original = parsed.get("size_rows_original") or []
        self.size_html_raw = parsed.get("size_html_raw") or ""

        from utils.detail_description_generator import normalize_size_chart
        from utils.detail_description_generator import (
            render_options_section,
            html_to_png_options,
            html_to_png_final
        )

        # ================================
        # ✔ 사이즈표 존재 여부 판단
        # ================================
        has_size_chart = (
            self.size_html_raw
            and self.size_headers_original
            and self.size_rows_original
        )

        # ================================
        # ✔ 사이즈표 HTML 생성
        # ================================
        if has_size_chart:
            try:
                self.size_html = normalize_size_chart(
                    self.size_headers_original,
                    self.size_rows_original
                )
            except Exception as e:
                print("[ERROR] normalize_size_chart 실패:", e)
                self.size_html = self.size_html_raw
        else:
            self.size_html = ""
            self.size_chart_image_path = None

        # ================================
        # ✔ 사이즈표 PNG 생성 — 존재할 때만
        # ================================
        if self.size_html:
            try:
                self.size_chart_image_path = html_to_png_final(self.size_html)
            except Exception as e:
                print("[ERROR] size PNG 생성 실패:", e)
                self.size_chart_image_path = None
        else:
            self.size_chart_image_path = None

        # ============================================================
        # 🔥 옵션 PNG 생성 — 옵션 있을 때만
        # ============================================================
        options_html = render_options_section(parsed.get("options", []))

        if options_html.strip():
            try:
                self.options_chart_path = html_to_png_options(options_html)
            except Exception as e:
                print("[ERROR] 옵션 PNG 생성 실패:", e)
                self.options_chart_path = None
        else:
            self.options_chart_path = None

        print("[load_data] 완료")

