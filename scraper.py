import time, re
import html_receiver
import urllib.parse
from browser_launcher import open_in_chrome
from parser_manager import ParserManager
from utils.utils_translator import translate_to_korean


# ------------------------------------------------------
# 한국어 여부 판단
# ------------------------------------------------------
def contains_korean(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"[가-힣]", text))


def refine_lens_products(lens_products):
    """
    변경된 규칙:
    1) name/url 없는 항목 제거
    2) URL 중복 제거
    3) 한국어 포함 여부만 먼저 판별 (번역 없음)
    4) 한국어 포함 상품 우선 정렬
    5) TOP5 선정
    6) 한국어 없는 상품만 번역 적용
    """

    print("────────────────────────────────────────")
    print("[Refine] 원본 lens_products 개수:", len(lens_products))
    print("────────────────────────────────────────")

    if not lens_products:
        print("[Refine] 입력 데이터 없음 → 빈 리스트 반환")
        return []

    # ---------------------------------------------------------
    # 1) name 또는 url 없는 항목 제거
    # ---------------------------------------------------------
    cleaned = []
    for p in lens_products:
        n = p.get("name")
        u = p.get("url")
        i = p.get("image", "")
        print(f"[Step1] name='{n}', url='{u}', image_type={'base64' if isinstance(i, str) and i.startswith('data:image') else 'url'}")

        if n and u:
            cleaned.append(p)
        else:
            print("   ↳ 제거됨 (name 또는 url 없음)")

    print("[Step1] 유효 항목 개수:", len(cleaned))

    # ---------------------------------------------------------
    # 2) URL 기준 중복 제거 (name 긴 항목 우선)
    # ---------------------------------------------------------
    unique = []
    seen = {}

    for p in cleaned:
        url = p["url"]
        name = p.get("name", "") or ""

        if url not in seen:
            seen[url] = len(unique)
            unique.append(p)
        else:
            existing_index = seen[url]
            existing_item = unique[existing_index]

            new_len = len(name.strip())
            old_len = len(existing_item.get("name", "").strip())

            if new_len > old_len:
                unique[existing_index] = p
                print(f"[Step2] URL 중복 → 더 긴 name 유지: '{name}' (기존 '{existing_item.get('name','')}')")
            else:
                print(f"[Step2] URL 중복 → 기존 항목 유지 (기존 name이 더 김)")

    print("[Step2] URL 중복 제거 후 개수:", len(unique))

    # ---------------------------------------------------------
    # 3) 한국어 포함 여부만 체크 (번역 금지)
    # ---------------------------------------------------------
    for p in unique:
        original_name = p.get("name", "").strip()
        has_ko = contains_korean(original_name)
        p["is_korean_original"] = has_ko
        print(f"[Step3] 한국어 포함 여부 체크 → '{original_name}' → 포함={has_ko}")

    # ---------------------------------------------------------
    # 4) 한국어 포함된 원본 우선
    # ---------------------------------------------------------
    korean_orig = [p for p in unique if p["is_korean_original"]]
    non_korean_orig = [p for p in unique if not p["is_korean_original"]]

    print(f"[Step4] 한국어 원본 개수: {len(korean_orig)}")
    print(f"[Step4] 비한국어 원본 개수: {len(non_korean_orig)}")

    # 🔥 한국어 포함된 항목들 → name 길이 기준 내림차순 정렬
    korean_orig.sort(key=lambda x: len(x.get("name", "").strip()), reverse=True)

    # 🔥 비한국어 항목도 동일하게 길이 기준 정렬해두면 품질↑
    non_korean_orig.sort(key=lambda x: len(x.get("name", "").strip()), reverse=True)

    # ---------------------------------------------------------
    # 5) 한국어 항목에서 TOP5 선정
    # ---------------------------------------------------------
    final = korean_orig[:5]
    print(f"[Step5] 한국어 원본 TOP5 개수: {len(final)}")

    # ---------------------------------------------------------
    # 6) 부족하면 비한국어 원본에서 채움
    # ---------------------------------------------------------
    if len(final) < 5:
        need = 5 - len(final)
        print(f"[Step6] 부족 {need}개 → 비한국어 원본에서 채움")
        final.extend(non_korean_orig[:need])

    print("[Step6] 최종 항목 개수:", len(final))


    # ---------------------------------------------------------
    # 7) 한국어 아닌 항목만 번역 적용
    # ---------------------------------------------------------
    for f in final:
        original_name = f.get("name", "").strip()

        if not f.get("is_korean_original"):  # 한국어 미포함일 때만 번역
            ko_name = translate_to_korean(original_name)
            print(f"[Step7] 번역 적용 → '{original_name}' → '{ko_name}'")
            f["name"] = ko_name
        else:
            print(f"[Step7] 번역 생략(한국어 포함) → '{original_name}'")

        # 내부 필드 제거
        f.pop("is_korean_original", None)

    print("────────────────────────────────────────")
    print("[Refine] 최종 반환 개수:", len(final))
    print("────────────────────────────────────────")

    return final



# ------------------------------------------------------
# Scraper
# ------------------------------------------------------
class Scraper:

    def __init__(self):
        self.parser_manager = ParserManager()

    # ------------------------------------------------------
    # HTML 수신 대기
    # ------------------------------------------------------
    def request_raw_html(self, url: str, color_code=None, timeout=60):
        print(f"[DEBUG] request_raw_html() 호출 → {url}")

        html_receiver.CAPTURED_HTML = None
        print("[DEBUG] CAPTURED_HTML 초기화 완료")
        
        if color_code:
            # 색상별 상세 HTML 요청
            capture_url = (
                f"{url}#program=SOEASY2&intent=RAW_COLOR&color={color_code}"
            )
        else:
            # 메인 페이지 HTML 요청
            capture_url = (
                f"{url}#program=SOEASY2&intent=RAW_MAIN"
            )

        open_in_chrome(capture_url)
        print("[DEBUG] 크롬 호출 완료:", capture_url)

        time.sleep(5.0)
        print("[DEBUG] 초기 5초 대기 완료")

        start = time.time()
        while time.time() - start < timeout:
            if html_receiver.CAPTURED_HTML:
                print("[DEBUG] CAPTURED_HTML 수신됨 → HTML 반환")
                return html_receiver.CAPTURED_HTML

            time.sleep(0.2)

        print("[DEBUG] request_raw_html TIMEOUT:", url)
        return None



    def start_lens_exact_match_search(self, results):
        # 옵션 대표 이미지(첫 번째 색상)
        colors = results.get("colors", [])
        if not colors:
            print("[Soeasy2] Lens 호출 불가: 색상 이미지 없음")
            return

        first_color = colors[0]
        first_image = first_color.get("image")

        if not first_image:
            print("[Soeasy2] Lens 호출 불가: 첫 번째 색상 대표 이미지 없음")
            return

        encoded = urllib.parse.quote_plus(first_image)

        # ★ Soeasy2 프로그램 식별용 hash 추가
        lens_url = (
            f"https://lens.google.com/uploadbyurl?url={encoded}"
            f"#program=SOEASY2&intent=LENS_MAIN"
        )

        print("[Soeasy2] Google Lens 호출 →", lens_url)
        open_in_chrome(lens_url)




    # ------------------------------------------------------
    # 전체 파이프라인
    # ------------------------------------------------------
    def collect(self, url: str):
    
        # ------------------------------------------------------
        # 1) 브랜드/국가 라우팅 → dict 반환
        # ------------------------------------------------------
        parser_info = self.parser_manager.get_parser(url)
        if not parser_info:
            return {"error": "지원되지 않는 사이트입니다."}

        parser = parser_info["parser"]      # 실제 파서 인스턴스
        brand = parser_info["brand"]        # "uniqlo"
        country = parser_info["country"]    # "jp", "us", "global"

        print(f"DEBUG parser_info = {parser_info}")
        print(f"DEBUG parser = {parser}, brand={brand}, country={country}")

        # ------------------------------------------------------
        # 2) HTML 가져오기
        # ------------------------------------------------------
        first_html = self.request_raw_html(url)
        if not first_html:
            return {"error": "HTML 수신 실패"}

        # ------------------------------------------------------
        # 3) 파싱 실행
        # ------------------------------------------------------
        results = parser.parse(
            first_html,
            request_raw_html=self.request_raw_html,
            original_url=url
        )

        import json
        print("\n===== [Soeasy2] 최종 파싱 결과 =====")
        print(json.dumps(results, ensure_ascii=False, indent=2))

        # ------------------------------------------------------
        # 4) Lens 수집 초기화
        # ------------------------------------------------------
        html_receiver.LENS_PRODUCTS = []   # 초기화
        self.start_lens_exact_match_search(results)

        # ------------------------------------------------------
        # 5) Lens 데이터 대기
        # ------------------------------------------------------
        lens_products = []
        timeout = 60
        start = time.time()

        print("[Soeasy2] Lens 데이터 대기 중...")

        while time.time() - start < timeout:
            lp = getattr(html_receiver, "LENS_PRODUCTS", [])
            if lp:
                lens_products = lp
                print(f"[Soeasy2] Lens 데이터 수신! ({len(lp)}개)")
                break
            time.sleep(0.2)

        if not lens_products:
            print("[Soeasy2] Lens 데이터 없음 → lens_products 비어 있음")

        # ------------------------------------------------------
        # 6) Lens 후처리
        # ------------------------------------------------------
        lens_products_refined = refine_lens_products(lens_products)

        # ------------------------------------------------------
        # 7) 파싱 + Lens + 브랜드/국가 정보 포함한 최종 반환 데이터
        # ------------------------------------------------------
        final_output = {
            "parsed": results,
            "lens_products": lens_products_refined,
            "brand": brand,
            "country": country
        }

        print("\n===== [Soeasy2] 최종 결과 (파싱 + Lens + brand/country) =====")
        print(json.dumps(final_output, ensure_ascii=False, indent=2))

        return final_output