# windly_uploader.py

import time, os, tempfile, struct
import win32clipboard, win32con
from playwright.sync_api import sync_playwright
import requests
from PIL import Image
import io
from automation.windly_config_loader import get_windly_temp_dir

WINDLY_LOGIN_URL = "https://hub.windly.cc/accounts/login"
WINDLY_INTEREST_URL = "https://global.windly.cc/view2/interested-product"

# ============================================================
# 1) CF_HDROP (파일 여러 개 붙여넣기)
# ============================================================
def create_explorer_hdrop(file_list):
    file_utf16_list = []
    for path in file_list:
        file_utf16_list.append(path.encode("utf-16le") + b"\x00\x00")
    file_block = b"".join(file_utf16_list) + b"\x00\x00"

    pFiles = struct.pack("<I", 20)
    flags = struct.pack("<I", 0)
    point = struct.pack("<ii", 0, 0)

    return pFiles + flags + point + file_block


def copy_files_to_clipboard(file_list):
    data = create_explorer_hdrop(file_list)
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
    win32clipboard.CloseClipboard()


# ============================================================
# 2) CF_DIB 이미지 1장 붙여넣기
# ============================================================
def copy_image_file(path):
    img = Image.open(path)
    if img.mode != "RGB":
        img = img.convert("RGB")

    output = io.BytesIO()
    img.save(output, "BMP")
    data = output.getvalue()[14:]  # DIB 부분
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    win32clipboard.CloseClipboard()


# ============================================================
# 3) 텍스트 복사
# ============================================================
def copy_text(text):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()


# ============================================================
# Windly Uploader
# ============================================================
class WindlyUploader:
    def __init__(self, user_id, user_pw, windly_temp_path=None):
        self.user_id = user_id
        self.user_pw = user_pw
        self.browser = None
        self.page = None
        self.p = None
        
        # windly_temp 경로만 사용 (생성 X)
        if windly_temp_path:
            self.windly_temp_path = windly_temp_path
        else:
            self.windly_temp_path = get_windly_temp_dir()

        # 폴더 없으면 생성
        
    def move_cursor_to_bottom(self):
        # 문서 맨 아래로 이동
        self.page.keyboard.down("Control")
        self.page.keyboard.press("End")
        self.page.keyboard.up("Control")
        time.sleep(0.05)

        # 빈 줄 추가 — 이미지 선택 해제용
        self.page.keyboard.press("Enter")
        time.sleep(0.05)
        
    def apply_font_large(self):
        size_button = self.page.locator("span.ql-picker-label")
        size_button.first.click()
        time.sleep(0.2)

        large_option = self.page.locator("span.ql-picker-item[data-value='large']")
        large_option.click()
        time.sleep(0.3)

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
    def goto_interest_page(self):
        for attempt in range(3):
            try:
                self.page.goto(WINDLY_INTEREST_URL, wait_until="domcontentloaded", timeout=90000)

                # URL이 목적지와 동일하면 성공
                if WINDLY_INTEREST_URL in self.page.url:
                    print("[Windly] Interested 상품 페이지 연결 완료")
                    return
            except:
                print(f"[WARN] 이동 실패 -> 재시도 {attempt+1}/3")

            time.sleep(3)

        print("[ERROR] Windly 상품 페이지 진입 완전 실패")

    # --------------------------------------------------------
    def prepare(self):
        if not self.browser:
            self.start_browser()
        self.login()
        self.goto_interest_page()

    # --------------------------------------------------------
    # 상품 검색 후 카드 클릭
    # --------------------------------------------------------
    def select_tag(self, tag_text):
        search_box = self.page.locator("input[placeholder='상품명 검색']")
        search_box.wait_for(state="visible")

        search_box.fill("")
        time.sleep(0.3)
        search_box.type(tag_text)
        time.sleep(0.5)

        self.page.keyboard.press("Enter")
        time.sleep(3)

        cards = self.page.locator("div.product-card")
        cnt = cards.count()

        if cnt == 0:
            print("검색 결과 없음")
            return False

        for i in range(cnt):
            card = cards.nth(i)
            text = card.inner_text()

            # 공백 제거 후 비교
            if tag_text.replace(" ", "") in text.replace(" ", ""):
                card.click()
                time.sleep(1)
                return True

        return False
    
    # ============================================================
    # 🔥 원본 상품 링크 수정 메소드 (popup → url 입력 → 저장)
    # ============================================================
    def update_original_url(self, url: str):
        print("[Windly] 상품 원본 URL 수정 시작")

        # 더보기 버튼
        self.page.locator("button.secondary.css-1k9mhp9.e2kkri01").click()
        time.sleep(0.8)

        # '상품 링크 수정' 버튼 (2번째)
        self.page.locator("div.css-7w0ojd.e10da43g1 button").nth(1).click()
        time.sleep(1)

        # 원본 URL 입력란
        input_box = self.page.locator("input[placeholder='새 링크를 입력해주세요']")
        input_box.fill("")
        input_box.type(url)
        time.sleep(0.6)

        # 🔥 저장 버튼(텍스트 기반 단일 식별)
        self.page.get_by_role("button", name="저장하기").click()

        print(f"[Windly] 원본 주소 업데이트 완료 → {url}")
        time.sleep(1.5)
        
    def apply_price_save(self):
        print("[Windly] 판매가 탭 이동 및 저장 시작")

        # 🔥 '판매가' 탭 클릭 (텍스트 기반 접근)
        self.page.get_by_role("button", name="판매가").click()
        time.sleep(1.5)

        # 🔥 '상품 판매가 변경' 버튼 클릭
        self.page.get_by_role("button", name="상품 판매가 변경").click()
        time.sleep(2)  # 팝업/입력창 로딩 대기

        # 🔥 저장 버튼 클릭 (color=blue / primary만 선택)
        self.page.locator("button.primary.css-o5l8yh.e2kkri01:has-text('저장')").click()

        print("[Windly] 판매가 저장 완료")
        time.sleep(1)


    # --------------------------------------------------------
    def open_detail_editor(self):
        self.page.locator("button:has-text('상세페이지')").first.click()
        time.sleep(2)

    # --------------------------------------------------------
    def clear_editor(self):
        editor = self.page.locator("div.ql-editor")
        editor.click()

        self.page.keyboard.down("Control")
        self.page.keyboard.press("A")
        self.page.keyboard.up("Control")

        self.page.keyboard.press("Delete")
        time.sleep(0.3)

    # --------------------------------------------------------
    # URL 리스트 → temp 파일 여러 개 다운로드
    # --------------------------------------------------------
    def download_temp_images(self, urls):
        files = []
        for idx, url in enumerate(urls):
            r = requests.get(url, timeout=5)

            filename = f"{idx:03d}_{os.path.basename(url)}"
            path = os.path.join(self.windly_temp_path, filename)

            with open(path, "wb") as f:
                f.write(r.content)

            files.append(path)

        return files

    
    def cleanup_windly_temp(self):
        try:
            for name in os.listdir(self.windly_temp_path):
                path = os.path.join(self.windly_temp_path, name)
                if os.path.isfile(path):
                    os.remove(path)
        except Exception as e:
            print(f"[WARN] windly_temp 정리 오류: {e}")

    def run_for_item(self, item):
        try:
            # 🚀 브라우저 새 실행
            self.p = sync_playwright().start()
            self.browser = self.p.chromium.launch(headless=False)
            self.page = self.browser.new_page()

            # 로그인 + 관심상품 페이지 진입
            self.page.goto(WINDLY_LOGIN_URL)
            self.page.fill("input[name='email']", self.user_id)
            self.page.fill("input[name='password']", self.user_pw)
            self.page.click("button[type='submit']")
            time.sleep(2)

            self.page.goto(WINDLY_INTEREST_URL, wait_until="domcontentloaded", timeout=90000)
            print("[Windly] 페이지 연결 완료")

            # ---------------- 상품 입력 프로세스 -----------------
            if not item.final_name:
                return False
                
            # ① 검색 → 카드 클릭
            if not self.select_tag(item.final_name):
                print("[Windly] 태그 매칭 실패 → 스킵")
                return False
            time.sleep(1)

            # ② 원본URL 업데이트
            self.update_original_url(item.url)
            
            # ②-1 판매가 저장 진행
            self.apply_price_save()

            # ③ 상세페이지 편집창
            self.open_detail_editor()
            editor = self.page.locator("div.ql-editor")
            editor.wait_for(state="visible")

            # ④ 내용 초기화 → 상품명 입력
            self.clear_editor()
            copy_text(item.final_name)
            editor.click()
            self.move_cursor_to_bottom()
            self.page.keyboard.press("Control+V")
            time.sleep(1)
            self.apply_font_large()
            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")

            # ⑤ 상품 이미지 입력
            print("[Windly] 이미지 업로드 시작")
            imgs = self.download_temp_images(item.parsed_raw.get("images", []))
            copy_files_to_clipboard(imgs)
            editor.click()
            self.move_cursor_to_bottom()
            self.page.keyboard.press("Control+V")
            time.sleep(2)

            # ⑥ 상세설명
            copy_text(item.final_detail_text or "")
            editor.click()
            self.move_cursor_to_bottom()
            self.page.keyboard.press("Control+V")
            time.sleep(1)

            # ⑦ 사이즈표
            if item.size_chart_image_path:
                copy_image_file(item.size_chart_image_path)
                editor.click()
                self.move_cursor_to_bottom()
                self.page.keyboard.press("Control+V")
                self.page.keyboard.press("Enter")

            # ⑧ 옵션표
            if item.options_chart_path:
                copy_image_file(item.options_chart_path)
                editor.click()
                self.move_cursor_to_bottom()
                self.page.keyboard.press("Control+V")

            print("===== Windly 입력 완료 =====")
            return True

        except Exception as e:
            print("[WINDLY ERROR]", e)
            return False

        finally:
            # 상품 1개 종료시 확실하게 브라우저 정리
            try:
                if hasattr(self, "page") and self.page: self.page.close()
                if hasattr(self, "browser") and self.browser: self.browser.close()
                if hasattr(self, "p") and self.p: self.p.stop()
            except:
                pass

            print("[Windly] 세션 종료 완료")
            self.cleanup_windly_temp()
