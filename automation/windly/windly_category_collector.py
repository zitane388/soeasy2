import os
import json
import time
from playwright.sync_api import sync_playwright

from automation.windly_config_loader import load_windly_config


WINDLY_LOGIN_URL = "https://hub.windly.cc/accounts/login"
WINDLY_INTEREST_URL = "https://global.windly.cc/view2/interested-product"

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)

OUTPUT_JSON = os.path.join(
    BASE_DIR,
    "category",
    "sources",
    "windly",
    "windly_categories.json"
)


def log(msg):
    print(f"[Windly] {msg}")


# ============================================================
# 공통: 이벤트 팝업 닫기
# ============================================================
def close_event_popup(page):
    time.sleep(2)
    try:
        btn = page.locator("button:has-text('오늘 하루 보지 않기')")
        if btn.is_visible():
            btn.click(force=True)
            log("이벤트 팝업 닫기")
            time.sleep(0.5)
    except:
        pass


# ============================================================
# 로그인 + 관심상품 페이지
# ============================================================
def login_and_goto_interest(page, user_id, user_pw):
    log("로그인 페이지 이동")
    page.goto(WINDLY_LOGIN_URL)
    page.wait_for_selector("input[name='email']", timeout=30000)

    page.fill("input[name='email']", user_id)
    page.fill("input[name='password']", user_pw)
    page.click("button[type='submit']")

    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)

    log("관심상품 페이지 이동")
    page.goto(WINDLY_INTEREST_URL, wait_until="domcontentloaded", timeout=90000)
    close_event_popup(page)


# ============================================================
# 첫 상품 카드 클릭
# ============================================================
def click_first_product_card(page):
    log("첫 상품 카드 클릭")
    link = page.locator("a[href^='/view2/interested-product/']").first
    link.wait_for(state="visible", timeout=30000)
    link.scroll_into_view_if_needed()
    link.click(force=True)

    page.wait_for_load_state("domcontentloaded")
    time.sleep(1)


# ============================================================
# 카테고리/태그 검색 → 템플릿 불러오기
# ============================================================
def open_template_popup(page):
    log("카테고리/태그 검색 클릭")
    page.locator("button:has-text('카테고리/태그 검색')").click(force=True)
    time.sleep(0.8)

    log("템플릿 불러오기 클릭")
    page.locator("button:has-text('템플릿 불러오기')").click(force=True)
    time.sleep(1)
    
def debug_popup_page(popup, tag=""):
    try:
        pages = popup.locator("button.normal.ebvjokl1.css-1ezgcz3.e2kkri01")
        enabled = []
        for i in range(pages.count()):
            btn = pages.nth(i)
            try:
                enabled.append(btn.is_enabled())
            except:
                enabled.append("ERR")

        print(f"[DEBUG]{tag} popup pagination buttons:", enabled)
    except Exception as e:
        print(f"[DEBUG]{tag} popup pagination error:", e)



# ============================================================
# 템플릿 팝업
# ============================================================
def get_template_popup(page):
    popup = page.locator(
        "div.ezzy6es7[width='600px']"
    ).filter(
        has=page.locator("div.ezzy6es5:has-text('템플릿 불러오기')")
    ).last

    popup.wait_for(state="visible", timeout=30000)
    log("템플릿 팝업 감지 완료")
    return popup


def get_template_rows(popup):
    rows = popup.locator("div.e1qo1yn83")
    log(f"템플릿 개수: {rows.count()}")
    return rows


# ============================================================
# 템플릿 키 추출
# ============================================================
def get_template_key(popup, idx):
    row = popup.locator("div.e1qo1yn83").nth(idx)
    key = row.locator("span.css-1rq4z3x").inner_text().strip()
    log(f"템플릿 키: {key}")
    return key


# ============================================================
# 카테고리 변경 감지용 유틸
# ============================================================
def read_market_value(page, market_title: str) -> str:
    blocks = page.locator("div.e1lwwc7f5")
    for i in range(blocks.count()):
        block = blocks.nth(i)
        title = block.locator("div.e1lwwc7f0").inner_text().strip()
        if title == market_title:
            span = block.locator("button span.css-1rq4z3x")
            if span.count() > 0:
                return span.first.inner_text().strip()
    return ""


def wait_until_category_applied(page, market_title, before_value, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        current = read_market_value(page, market_title)
        if current and current != before_value:
            return True
        time.sleep(0.2)
    return False


# ============================================================
# n번째 템플릿 불러오기
# ============================================================
def click_template_by_index(page, popup, idx):
    log(f"템플릿 {idx + 1} 불러오기 클릭")

    before = read_market_value(page, "스마트스토어 카테고리")

    row = popup.locator("div.e1qo1yn83").nth(idx)
    load_btn = row.locator("button:has-text('불러오기')")

    load_btn.wait_for(state="visible", timeout=20000)
    load_btn.scroll_into_view_if_needed()
    load_btn.click(force=True)

    ok = wait_until_category_applied(page, "스마트스토어 카테고리", before)
    if not ok:
        log("[WARN] 카테고리 변경 감지 실패")

    log(f"템플릿 {idx + 1} 적용 완료 (변경 확인)")


# ============================================================
# 🔥 카테고리 수집 (중복 마켓 차단 – 핵심 수정)
# ============================================================
def collect_categories(page):
    as_dict = {}

    blocks = page.locator("div.e1lwwc7f5")
    log(f"카테고리 블록 수: {blocks.count()}")

    for i in range(blocks.count()):
        block = blocks.nth(i)
        title = block.locator("div.e1lwwc7f0").inner_text().strip()

        if title in as_dict:
            continue

        span = block.locator("button span.css-1rq4z3x")
        if span.count() == 0:
            log(f" - {title}: 값 없음")
            continue

        value = span.first.inner_text().strip()
        if not value:
            log(f" - {title}: 빈 값")
            continue

        log(f" - {title}: {value}")
        as_dict[title] = value

    log(f"수집된 카테고리 {len(as_dict)}개")
    return as_dict



def goto_next_page(page) -> bool:
    # ▶ 아이콘 (다음 페이지)만 포함한 버튼
    next_btn = page.locator(
        "button:has(svg path[d^='M8.59 16.59L13.17 12'])"
    )

    if next_btn.count() == 0:
        log("다음 페이지 버튼 없음 → 종료")
        return False

    btn = next_btn.first

    if not btn.is_visible():
        log("다음 페이지 버튼 비활성 → 종료")
        return False

    btn.scroll_into_view_if_needed()
    btn.click(force=True)

    # 페이지 전환 대기 (짧게)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(0.3)

    return True


def popup_click_next(page):
    """
    템플릿 팝업 내부의 단일 > 버튼만 클릭
    (네가 준 SVG path 기준)
    """
    single_path = "M8.59 16.59L13.17 12L8.59 7.41L10 6L16 12L10 18L8.59 16.59Z"

    btn = page.locator(f"button:has(svg path[d='{single_path}'])").last
    if btn.count() == 0:
        return False

    try:
        if btn.is_disabled():
            return False
    except:
        pass

    btn.click(force=True)
    time.sleep(0.2)
    return True


def restore_popup_page(page, popup_page_idx):
    """
    팝업이 다시 열렸을 때
    이전에 있던 페이지까지 > 버튼으로 복원
    """
    if popup_page_idx <= 1:
        return

    for _ in range(popup_page_idx - 1):
        ok = popup_click_next(page)
        if not ok:
            break


def main():
    user_id, user_pw = load_windly_config()
    log("스크립트 시작")

    json_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # 1️⃣ 로그인 + 관심상품 페이지
        login_and_goto_interest(page, user_id, user_pw)

        # 2️⃣ 첫 상품 클릭 (단 한 번)
        click_first_product_card(page)

        popup_page_idx = 1  # 🔥 템플릿 팝업 페이지 상태

        while True:
            log(f"===== TEMPLATE POPUP PAGE {popup_page_idx} =====")

            # 3️⃣ 팝업 열기
            open_template_popup(page)
            popup = get_template_popup(page)

            # 🔥 핵심: 팝업 페이지 복원
            restore_popup_page(page, popup_page_idx)

            rows = get_template_rows(popup)
            total = rows.count()
            log(f"템플릿 개수: {total}")

            if total == 0:
                log("템플릿 없음 → 종료")
                break

            # 4️⃣ 현재 팝업 페이지의 템플릿 전부 처리
            for i in range(total):
                template_key = get_template_key(popup, i)

                click_template_by_index(page, popup, i)

                category_dict = collect_categories(page)

                json_results.append({
                    "template_key": template_key,
                    "categories": category_dict
                })

                # ⚠️ 불러오기 누르면 팝업 닫힘 → 다시 열어야 함
                open_template_popup(page)
                popup = get_template_popup(page)

                # 🔥 다시 현재 페이지 복원
                restore_popup_page(page, popup_page_idx)

            # 5️⃣ 다음 템플릿 페이지로 이동 (팝업 내부 > 버튼)
            moved = popup_click_next(page)
            if not moved:
                log("다음 템플릿 페이지 없음 → 전체 종료")
                break

            popup_page_idx += 1
            time.sleep(0.3)

        browser.close()

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(json_results, f, ensure_ascii=False, indent=2)

    log(f"JSON 저장 완료: {OUTPUT_JSON}")
    log("전체 템플릿 수집 종료")




if __name__ == "__main__":
    main()
