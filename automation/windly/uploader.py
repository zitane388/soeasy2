import time
import os
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
    def apply_price_save(self):
        print("[Windly] 판매가 탭 이동 및 저장 시작")

        self.page.get_by_role("button", name="판매가").click()
        time.sleep(1.5)

        self.page.get_by_role("button", name="상품 판매가 변경").click()
        time.sleep(2)

        self.page.locator("button.primary.css-o5l8yh.e2kkri01:has-text('저장')").click()

        print("[Windly] 판매가 저장 완료")
        time.sleep(1)

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
            item.size_chart_image_path = None
            if not getattr(item, "options_chart_path", None):
                options_html = render_options_section(item.parsed_raw.get("options", []))
                if options_html and options_html.strip():
                    item.options_chart_path = os.path.abspath(
                        stabilize_png_file(html_to_png_options(options_html))
                    )
                    print("[Windly PRE] 옵션표 PNG 생성 완료")
                else:
                    print("[Windly PRE] 옵션 데이터 없음")

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
            self.apply_price_save()

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

            # ⑤ 상품 이미지 입력
            print("[Windly] 이미지 업로드 시작 (1장씩)")
            
            # 1. 옵션 이미지 URL 수집
            option_imgs = []
            for opt in item.parsed_raw.get("options", []):
                for v in opt.get("values", []):
                    img = v.get("image")
                    if isinstance(img, str) and img.startswith("http"):
                        option_imgs.append(img)

            # 2. 전체 이미지 중 옵션 이미지를 제외하고 다운로드
            raw_images = item.parsed_raw.get("images", []) or []
            # 옵션 이미지 URL 리스트에 포함되지 않은 이미지만 필터링
            filtered_raw_images = [url for url in raw_images if url not in option_imgs]

            imgs = download_temp_images(
                filtered_raw_images, # 필터링된 리스트 전달
                self.windly_temp_path
            )
            
            # 3. 대표 이미지(가공 썸네일) 처리
            thumb = getattr(item, "make_thumbnail_img", None)
            if thumb:
                thumb_path = os.path.abspath(thumb)
                if os.path.exists(thumb_path):
                    # 이미 다운로드된 목록에 중복이 있다면 제거 (경로 기준)
                    imgs = [p for p in imgs if os.path.abspath(p) != thumb_path]
                    imgs.insert(0, thumb_path)

            # ... 이후 업로드 루프(for img_path in imgs)는 동일

            print("[Windly] 최종 이미지 순서:")
            for i, pth in enumerate(imgs):
                print(f"  {i+1}. {os.path.basename(pth)}")

            for img_path in imgs:
                copy_image_file(img_path)   # CF_DIB (단일 이미지)
                editor.click()
                move_cursor_to_bottom(self.page)
                self.page.keyboard.press("Control+V")

                # DOM 안정화 대기 (중요)
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
            if item.options_chart_path:
                print("[WINDLY] 옵션표 붙여넣기 시도")
                copy_image_file(item.options_chart_path)
                editor.click()
                move_cursor_to_bottom(self.page)
                self.page.keyboard.press("Enter")
                time.sleep(0.5)
                self.page.keyboard.press("Control+V")
                self.page.keyboard.press("Enter")
                time.sleep(2)
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
