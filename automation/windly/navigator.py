import time

WINDLY_LOGIN_URL = "https://hub.windly.cc/accounts/login"
WINDLY_INTEREST_URL = "https://global.windly.cc/view2/interested-product"


def goto_interest_page(page):
    for attempt in range(3):
        try:
            page.goto(WINDLY_INTEREST_URL, wait_until="domcontentloaded", timeout=90000)
            if WINDLY_INTEREST_URL in page.url:
                print("[Windly] Interested 상품 페이지 연결 완료")
                return True
        except Exception:
            print(f"[WARN] 이동 실패 -> 재시도 {attempt+1}/3")

        time.sleep(3)

    print("[ERROR] Windly 상품 페이지 진입 완전 실패")
    return False


def close_event_popup(page):
    print("[Windly] 팝업 로딩을 위해 2초간 대기합니다...")
    time.sleep(3)

    try:
        popup_button = page.locator("button:has-text('오늘 하루 보지 않기')")
        if popup_button.is_visible():
            popup_button.click(force=True)
            print("[Windly] 이벤트 팝업 발견 -> '오늘 하루 보지 않기' 클릭 완료")
            time.sleep(0.5)
        else:
            print("[Windly] 2초 대기 후 확인 결과, 팝업이 없습니다.")
    except Exception as e:
        print(f"[Windly] 팝업 처리 중 알 수 없는 오류(무시 가능): {e}")
