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
        self.page.goto(WINDLY_INTEREST_URL)
        self.page.wait_for_load_state("domcontentloaded")
        time.sleep(1)

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
        for url in urls:
            r = requests.get(url, timeout=5)

            ext = ".jpg"
            path = os.path.join(
                self.windly_temp_path,
                f"windly_img_{int(time.time() * 1000)}_{os.path.basename(url)}"
            )

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

    # --------------------------------------------------------
    # Windly 입력
    # --------------------------------------------------------
    def run_for_item(self, item):
    
        final_name = getattr(item, "final_name", None)
        if not final_name or not final_name.strip():
            print("[Windly] final_name 없음 → 해당 상품 스킵")
            return

        # ------------------------------------------
        # STEP 0: 영상 파일 생성 (필요 시)
        # ------------------------------------------
        # if item.video_url:
        #     from utils.video_utils import download_and_convert_video
        #     mp4_path = download_and_convert_video(item.video_url)
        #     if mp4_path:
        #         item.video_file = mp4_path
        #     else:
        #         item.video_file = None
        # else:
        #     item.video_file = None

        # 1) 태그 선택
        if not self.select_tag(item.final_name):
            print("[Windly] 태그 선택 실패 → 상품 스킵")
            return
        self.open_detail_editor()

        # 2) 에디터 확보
        editor = self.page.locator("div.ql-editor")
        editor.wait_for(state="visible")

        # 3) 기존 내용 삭제
        self.clear_editor()

        # ------------------------------------------
        # STEP 1: 상품명 텍스트
        # ------------------------------------------
        copy_text(item.final_name)
        editor.click()
        self.move_cursor_to_bottom()
        self.page.keyboard.press("Control+V")
        time.sleep(1)

        self.page.keyboard.down("Control")
        self.page.keyboard.press("A")
        self.page.keyboard.up("Control")

        self.apply_font_large()

        self.page.keyboard.press("End")
        self.page.keyboard.press("Enter")
        self.page.keyboard.press("Enter")
            
        # ------------------------------------------
        # STEP 3: 상품 이미지
        # ------------------------------------------
        print("[Windly] 상품이미지 입력 (CF_HDROP)")

        temp_files = self.download_temp_images(item.parsed_raw.get("images", []))

        copy_files_to_clipboard(temp_files)

        editor.click()
        self.move_cursor_to_bottom()
        self.page.keyboard.press("Control+V")
        time.sleep(3)

        self.move_cursor_to_bottom()

        # ------------------------------------------
        # STEP 4: 상세설명 텍스트
        # ------------------------------------------
        desc = item.final_detail_text or ""
        copy_text(desc)

        editor.click()
        self.move_cursor_to_bottom()
        self.page.keyboard.press("Control+V")
        time.sleep(1.2)

        # ------------------------------------------
        # STEP 5: 사이즈표 이미지
        # ------------------------------------------
        if item.size_chart_image_path:
            copy_image_file(item.size_chart_image_path)
            editor.click()
            self.move_cursor_to_bottom()
            self.page.keyboard.press("Control+V")
            time.sleep(1)

            self.page.keyboard.press("Enter")
            self.page.keyboard.press("Enter")

        # ------------------------------------------
        # STEP 6: 옵션 이미지
        # ------------------------------------------
        if item.options_chart_path:
            copy_image_file(item.options_chart_path)
            editor.click()
            self.move_cursor_to_bottom()
            self.page.keyboard.press("Control+V")
            time.sleep(1)

        time.sleep(3)
        print("===== Windly 입력 완료 =====")

        # windly_temp 폴더 정리
        self.cleanup_windly_temp()