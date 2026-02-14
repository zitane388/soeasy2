import time
import os
import re
from playwright.sync_api import sync_playwright

from automation.windly_config_loader import get_windly_temp_dir
from .clipboard_utils import copy_files_to_clipboard, copy_image_file, copy_text
from .editor_utils import move_cursor_to_bottom, apply_font_large, open_detail_editor, clear_editor
from .navigator import WINDLY_LOGIN_URL, WINDLY_INTEREST_URL, goto_interest_page, close_event_popup
from .temp_file_manager import download_temp_images, cleanup_windly_temp


class WindlyUploader:
    def __init__(self, user_id, user_pw, windly_temp_path=None):
        self.user_id = user_id
        self.user_pw = user_pw
        self.browser = None
        self.page = None
        self.p = None

        self.windly_temp_path = windly_temp_path or get_windly_temp_dir()
        if not os.path.exists(self.windly_temp_path):
            os.makedirs(self.windly_temp_path, exist_ok=True)
        self.windly_temp_path = os.path.abspath(self.windly_temp_path)

    # --------------------------------------------------------
    def start_browser(self):
        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch(headless=False)
        self.page = self.browser.new_page()

    # --------------------------------------------------------
    def login(self):
        self.page.goto(WINDLY_LOGIN_URL)
        self.page.wait_for_selector("input[name='email']")

        self.page.fill("input[name='email']", self.user_id)
        self.page.fill("input[name='password']", self.user_pw)
        self.page.click("button[type='submit']")
        time.sleep(2)

    # --------------------------------------------------------
    def prepare(self):
        if not self.browser:
            self.start_browser()
        self.login()
        goto_interest_page(self.page)

    # --------------------------------------------------------
    def select_tag(self, tag_text):
        search_box = self.page.locator("input[placeholder='상품명 검색']")
        search_box.wait_for(state="visible")

        search_box.fill("")
        time.sleep(0.3)
        search_box.type(tag_text)
        time.sleep(0.5)

        self.page.keyboard.press("Enter")
        time.sleep(5)

        cards = self.page.locator("div.product-card")
        cnt = cards.count()

        if cnt == 0:
            print("검색 결과 없음")
            return False

        for i in range(cnt):
            card = cards.nth(i)
            text = card.inner_text()

            if tag_text.replace(" ", "") in text.replace(" ", ""):
                card.click()
                time.sleep(1)
                return True

        return False
    
    # ============================================================
    # 카테고리 템플릿 자동 적용 (속도 최적화 버전)
    # ============================================================
    def apply_category_template(self, template_key: str):
        if not template_key:
            print("[Windly] template_key 없음 → 카테고리 스킵")
            return

        page = self.page
        print(f"[Windly] 카테고리 템플릿 적용 시도: {template_key}")

        # 1️⃣ 카테고리/태그 검색
        page.locator("button:has-text('카테고리/태그 검색')").click(force=True)
        time.sleep(0.3)

        # 2️⃣ 템플릿 불러오기 (헤더 버튼)
        page.locator("button:has-text('템플릿 불러오기')").first.click(force=True)
        time.sleep(0.3)

        # 3️⃣ 팝업 확보
        popup = page.locator(
            "div.ezzy6es7[width='600px']"
        ).filter(
            has=page.locator("div.ezzy6es5:has-text('템플릿 불러오기')")
        ).last

        popup.wait_for(state="visible", timeout=5000)

        # 4️⃣ 템플릿 제목 검색
        search_input = popup.locator('input[placeholder="템플릿 제목 검색"]')
        search_input.fill("")
        search_input.type(template_key, delay=30)
        page.keyboard.press("Enter")

        # 5️⃣ backdrop이 "있을 때만" 짧게 제거 대기
        if page.locator("div.backdrop_visible").count() > 0:
            try:
                page.wait_for_selector(
                    "div.backdrop_visible",
                    state="detached",
                    timeout=2000
                )
            except:
                pass

        # 6️⃣ 첫 번째 템플릿 불러오기 (즉시 클릭)
        popup.locator(
            "div.e1qo1yn83 >> button:has-text('불러오기')"
        ).first.click(force=True)

        # 7️⃣ 불러오기 후 backdrop 처리 (짧게)
        if page.locator("div.backdrop_visible").count() > 0:
            try:
                page.wait_for_selector(
                    "div.backdrop_visible",
                    state="detached",
                    timeout=2000
                )
            except:
                pass

        # 8️⃣ 적용하기 버튼 즉시 클릭
        page.locator(
            "button:has(span:has-text('적용하기'))"
        ).click(force=True)

        print(f"[Windly] 카테고리 템플릿 적용 완료: {template_key}")



    # ============================================================
    # 원본 상품 링크 수정
    # ============================================================
    def update_original_url(self, url: str):
        print("[Windly] 상품 원본 URL 수정 시작")

        self.page.locator("button.secondary.css-1k9mhp9.e2kkri01").click()
        time.sleep(0.8)

        self.page.locator("div.css-7w0ojd.e10da43g1 button").nth(1).click()
        time.sleep(1)

        input_box = self.page.locator("input[placeholder='새 링크를 입력해주세요']")
        input_box.fill("")
        input_box.type(url)
        time.sleep(0.6)

        self.page.get_by_role("button", name="저장하기").click()

        print(f"[Windly] 원본 주소 업데이트 완료 → {url}")
        time.sleep(1.5)

    # ============================================================
    # 판매가 탭 저장
    # ============================================================
    def apply_price_save(self, item=None):
        print("[Windly] 판매가 탭 이동 및 저장 시작")

        self.page.get_by_role("button", name="판매가").click()
        time.sleep(0.5)

        self.page.get_by_role("button", name="상품 판매가 변경").click()
        time.sleep(0.8)

        try:
            source_currency_code = str(getattr(item, "price_currency", "") or "").strip().upper()
            target_currency_code = "KRW" if source_currency_code == "VND" else source_currency_code

            if target_currency_code:
                # 1) target 통화를 포함한 박스 찾기
                selected = False
                currency_box = self.page.locator(
                    f"div.e1lwwc7f4:has(input[type='radio'][value='{target_currency_code}'])"
                ).first
                if currency_box.count() == 0:
                    currency_box = self.page.locator("div.e1lwwc7f4:has(button.css-1mb5vlr)").first

                # 2) 드롭다운 버튼 먼저 클릭(필수)
                if currency_box.count() > 0:
                    btn = currency_box.locator("button.css-1mb5vlr").first
                    if btn.count() > 0:
                        btn.scroll_into_view_if_needed()
                        btn.click(force=True, timeout=3000)
                        time.sleep(0.25)

                # 3) value 라디오 선택
                target_radio = self.page.locator(
                    f"input[type='radio'][value='{target_currency_code}']"
                ).first
                if target_radio.count() > 0:
                    try:
                        if not target_radio.is_checked():
                            target_radio.check(force=True, timeout=3000)
                            time.sleep(0.15)
                        selected = True
                    except Exception:
                        # fallback: label 클릭
                        radio_id = target_radio.get_attribute("id")
                        if radio_id:
                            label = self.page.locator(f"label[for='{radio_id}']").first
                            if label.count() > 0 and label.is_visible():
                                label.click(force=True, timeout=3000)
                                time.sleep(0.15)
                                selected = True

                if not selected:
                    print(f"[Windly][WARN] 통화 선택 대상 없음/선택 실패: {target_currency_code}")

                checked = self.page.locator("input[type='radio']:checked").first
                current_code = (checked.get_attribute("value") or "").strip().upper() if checked.count() > 0 else ""
                if current_code == target_currency_code:
                    print(f"[Windly] 통화 설정 완료: {source_currency_code} -> {current_code}")
                else:
                    print(f"[Windly][WARN] 통화 불일치 target={target_currency_code}, current={current_code}")
            else:
                print("[Windly][WARN] 통화 코드 없음")
        except Exception as e:
            print(f"[Windly][WARN] 통화 선택 실패: {e}")

        self.page.get_by_role("button", name="저장").click()

        print("[Windly] 판매가 저장 완료")
        time.sleep(0.3)

    # ============================================================
    # 원가 일괄 변경
    # ============================================================
    def apply_original_cost_bulk(self, item=None):
        def parse_cost_value(raw):
            if raw is None:
                return None
            if isinstance(raw, (int, float)):
                return int(raw)
            s = str(raw)
            nums = re.findall(r"\d[\d,]*", s)
            if not nums:
                return None
            digits = re.sub(r"[^\d]", "", nums[0])
            return int(digits) if digits else None

        source_currency_code = str(getattr(item, "price_currency", "") or "").strip().upper() if item else ""
        if source_currency_code == "VND" and item:
            raw_cost = getattr(item, "base_price_krw", None)
        else:
            raw_cost = getattr(item, "base_price", None) if item else None

        cost_value = parse_cost_value(raw_cost)
        if not cost_value:
            print(f"[Windly][WARN] 원가 입력값 없음: base_price={raw_cost}")
            return

        print(f"[Windly] 원가 일괄 변경 시작: {cost_value}")
        try:
            self.page.get_by_role("button", name="일괄 변경").first.click()
            time.sleep(0.4)

            self.page.get_by_role("button", name="원가 일괄 변경").first.click()
            time.sleep(0.6)

            popup = self.page.locator("div.ezzy6es7").filter(
                has=self.page.locator("div.ezzy6es5:has-text('원가 일괄 변경')")
            ).last
            popup.wait_for(state="visible", timeout=5000)

            input_box = popup.locator("input[type='text']").first
            input_box.click()
            input_box.press("Control+A")
            input_box.fill("")
            input_box.type(str(cost_value), delay=10)
            time.sleep(0.2)

            popup.get_by_role("button", name="적용하기").first.click()
            time.sleep(0.8)
            print("[Windly] 원가 일괄 변경 완료")
        except Exception as e:
            print(f"[Windly][WARN] 원가 일괄 변경 실패: {e}")

    # --------------------------------------------------------
    def run_for_item(self, item):
        try:
            print(f"[Windly] '{item.final_name}' 작업 시작 - 임시 폴더 정리 중...")
            cleanup_windly_temp(self.windly_temp_path)

            # 브라우저 새 실행
            self.p = sync_playwright().start()
            self.browser = self.p.chromium.launch(headless=False)
            self.page = self.browser.new_page()

            # 로그인 페이지 진입
            self.page.goto(WINDLY_LOGIN_URL)

            # ======================================================
            # 로그인 입력 전에 PNG 생성 (원본 로직 유지)
            # ======================================================
            from utils.detail_description_generator import (
                render_options_section,
                html_to_png_options,
                html_to_png_final
            )
            from utils.file_stabilizer import stabilize_png_file

            item.options_chart_path = None
            item.options_chart_paths = []
            item.size_chart_image_path = None
            if not getattr(item, "options_chart_path", None):
                option_groups = item.parsed_raw.get("options", [])
                option_card_paths = []
                card_idx = 1

                for group in option_groups:
                    values = group.get("values", []) if isinstance(group, dict) else []
                    for value in values:
                        if not isinstance(value, dict):
                            continue
                        if not value.get("image"):
                            continue

                        single_group = [
                            {
                                "group_name": group.get("group_name", ""),
                                "values": [value],
                            }
                        ]
                        card_html = render_options_section(single_group, item=item)
                        if not card_html or not card_html.strip():
                            continue

                        out_name = f"options_card_{card_idx:03d}.png"
                        card_path = html_to_png_options(card_html, output_name=out_name)
                        option_card_paths.append(os.path.abspath(stabilize_png_file(card_path)))
                        card_idx += 1

                item.options_chart_paths = option_card_paths
                item.options_chart_path = option_card_paths[0] if option_card_paths else None
                if option_card_paths:
                    print(f"[Windly PRE] 옵션카드 PNG 생성 완료: {len(option_card_paths)}장")
                else:
                    print("[Windly PRE] 옵션카드 데이터 없음")

            if not getattr(item, "size_chart_image_path", None):
                raw_size_html = (
                    getattr(item, "size_html", None)
                    or item.parsed_raw.get("size_html", "")
                )
                if raw_size_html and raw_size_html.strip():
                    item.size_chart_image_path = os.path.abspath(
                        stabilize_png_file(html_to_png_final(raw_size_html))
                    )
                    print("[Windly PRE] 사이즈표 PNG 생성 완료")
                else:
                    print("[Windly PRE] 사이즈표 데이터 없음")

            # ======================================================
            # 로그인
            # ======================================================
            self.page.fill("input[name='email']", self.user_id)
            self.page.fill("input[name='password']", self.user_pw)
            self.page.click("button[type='submit']")
            time.sleep(2)

            self.page.goto(WINDLY_INTEREST_URL, wait_until="domcontentloaded", timeout=90000)
            print("[Windly] 페이지 연결 완료")

            close_event_popup(self.page)

            if not item.final_name:
                return False

            # ① 검색 → 카드 클릭
            if not self.select_tag(item.final_name):
                print("[Windly] 태그 매칭 실패 → 스킵")
                return False
            time.sleep(1)
            
            # ① 카테고리 템플릿 적용
            template_key = getattr(item, "matched_category_template_key", None)
            if template_key:
                self.apply_category_template(template_key)
                time.sleep(1)
            else:
                print("[Windly] matched_category_template_key 없음 → 카테고리 스킵")
            time.sleep(5)
            
            # ② 원본URL 업데이트
            self.update_original_url(item.url)

            # ②-1 판매가 저장
            self.apply_price_save(item)
            self.apply_original_cost_bulk(item)

            # ③ 상세페이지 편집창
            open_detail_editor(self.page)
            editor = self.page.locator("div.ql-editor")
            editor.wait_for(state="visible")

            # ④ 내용 초기화
            clear_editor(self.page)
            time.sleep(0.2)

            # ④-1 상품명 붙여넣기
            copy_text(item.final_name)
            editor.click()
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            time.sleep(0.1)
            self.page.keyboard.press("Control+V")
            time.sleep(0.3)

            # ④-2 상품명 전체 선택
            self.page.keyboard.down("Control")
            self.page.keyboard.press("A")
            self.page.keyboard.up("Control")
            time.sleep(0.2)

            # ④-3 글씨 크게 적용
            apply_font_large(self.page)
            time.sleep(0.2)

            move_cursor_to_bottom(self.page)
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            time.sleep(0.5)

            # ======================================================
            # ⑤ 상품 이미지 입력 (옵션 이미지 제외, 로고 제거 반영)
            # ======================================================
            print("[Windly] 이미지 업로드 시작 (1장씩)")

            # ------------------------------------------------------
            # 1. 옵션 이미지 URL 수집 (원본 기준)
            # ------------------------------------------------------
            option_image_urls = set()

            for opt in item.parsed_raw.get("options", []):
                for v in opt.get("values", []):
                    img = v.get("image")
                    if isinstance(img, str) and img.startswith("http"):
                        option_image_urls.add(img)

            # ------------------------------------------------------
            # 2. logo_job_results 기반 파일 → 원본 URL 매핑
            # ------------------------------------------------------
            file_to_original_url = {}

            for r in getattr(item, "logo_job_results", []) or []:
                url = r.get("url")
                fp = r.get("file_path")
                if url and fp:
                    file_to_original_url[os.path.abspath(fp)] = url

            # ------------------------------------------------------
            # 3. 옵션 이미지 판별 함수
            # ------------------------------------------------------
            def is_option_image(src: str) -> bool:
                # URL인 경우
                if src.startswith("http"):
                    return src in option_image_urls

                # 파일 경로인 경우 → 원본 URL로 환원
                src_abs = os.path.abspath(src)
                original_url = file_to_original_url.get(src_abs)
                if original_url:
                    return original_url in option_image_urls

                return False

            # ------------------------------------------------------
            # 4. 최종 업로드 대상 이미지 결정 (입력 순서 그대로 유지)
            # ------------------------------------------------------
            raw_sources = item.final_image_sources or []
            normalized_sources = []

            for src in raw_sources:
                if isinstance(src, str) and src.strip():
                    normalized_sources.append(src.strip())
                elif isinstance(src, (list, tuple)):
                    for inner in src:
                        if isinstance(inner, str) and inner.strip():
                            normalized_sources.append(inner.strip())

            upload_sources = [
                src for src in normalized_sources
                if not is_option_image(src)
            ]

            # ------------------------------------------------------
            # 5. URL / 파일 혼합 다운로드 처리
            # ------------------------------------------------------
            imgs = []

            for src in upload_sources:
                if src.startswith("http"):
                    downloaded_files, _ = download_temp_images([src], self.windly_temp_path)
                    imgs.extend(downloaded_files)
                else:
                    imgs.append(os.path.abspath(src))

            # ------------------------------------------------------
            # 6. 업로드 실행
            # ------------------------------------------------------
            print("[Windly] 최종 이미지 순서:")
            for i, pth in enumerate(imgs):
                print(f"  {i+1}. {os.path.basename(pth)}")

            for img_path in imgs:
                copy_image_file(img_path)
                editor.click()
                move_cursor_to_bottom(self.page)
                self.page.keyboard.press("Control+V")
                time.sleep(0.5)

            time.sleep(2)


            move_cursor_to_bottom(self.page)
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")
            time.sleep(0.5)

            # ⑥ 상세설명
            copy_text(item.final_detail_text or "")
            editor.click()
            move_cursor_to_bottom(self.page)
            self.page.keyboard.press("Enter")
            time.sleep(0.5)
            self.page.keyboard.press("Control+V")
            time.sleep(2)

            self.page.keyboard.press("Enter")
            time.sleep(0.3)

            # ⑦ 사이즈표
            if item.size_chart_image_path:
                print("[WINDLY] 사이즈표 붙여넣기 시도")
                copy_image_file(item.size_chart_image_path)
                editor.click()
                move_cursor_to_bottom(self.page)
                self.page.keyboard.press("Enter")
                time.sleep(0.5)
                self.page.keyboard.press("Control+V")
                self.page.keyboard.press("Enter")
                time.sleep(2)
            else:
                print("[WINDLY] 사이즈표 없음 → 스킵")

            # ⑧ 옵션표
            option_paths = getattr(item, "options_chart_paths", None) or (
                [item.options_chart_path] if item.options_chart_path else []
            )
            if option_paths:
                print("[WINDLY] 옵션카드 붙여넣기 시도")
                for part_idx, option_path in enumerate(option_paths, start=1):
                    print(f"[WINDLY] 옵션카드 붙여넣기 {part_idx}/{len(option_paths)}")
                    copy_image_file(option_path)
                    editor.click()
                    move_cursor_to_bottom(self.page)
                    self.page.keyboard.press("Enter")
                    time.sleep(0.5)
                    self.page.keyboard.press("Control+V")
                    self.page.keyboard.press("Enter")
                    time.sleep(1.2)
            else:
                print("[WINDLY] 옵션표 없음 → 스킵")

            print("===== Windly 입력 완료 =====")
            return True

        except Exception as e:
            print("[WINDLY ERROR]", e)
            return False

        finally:
            try:
                if hasattr(self, "page") and self.page:
                    self.page.close()
                if hasattr(self, "browser") and self.browser:
                    self.browser.close()
                if hasattr(self, "p") and self.p:
                    self.p.stop()
            except Exception:
                pass

            print("[Windly] 세션 종료 완료")
            cleanup_windly_temp(self.windly_temp_path)
