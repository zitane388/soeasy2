# smartstore_login.csv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import requests


SMARTSTORE_LOGIN_URL = "https://sell.smartstore.naver.com/#/login"
SMARTSTORE_BASE = "https://sell.smartstore.naver.com"


class SmartStoreLoginError(Exception):
    pass


def login_and_create_session(
    *,
    naver_id: str,
    naver_pw: str,
    headless: bool = False,
) -> requests.Session:
    """
    SmartStore 실제 로그인 → requests.Session 반환
    (React controlled input 네이티브 setter 대응 최종본)
    """

    if not naver_id or not naver_pw:
        raise SmartStoreLoginError("naver_id / naver_pw가 전달되지 않았습니다")

    cookies = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 로그인 페이지
            page.goto(SMARTSTORE_LOGIN_URL, wait_until="networkidle")

            # 입력창 로드 대기
            page.wait_for_selector("input.Login_ipt__6a-x7", timeout=20000)

            # -------------------------------------------------
            # 🔥 네이티브 value setter + input/change 이벤트
            # -------------------------------------------------
            page.evaluate(
                """([id, pw]) => {
                    const inputs = document.querySelectorAll("input.Login_ipt__6a-x7");
                    if (inputs.length < 2) {
                        throw new Error("login inputs not found");
                    }

                    const setValue = (el, value) => {
                        const setter = Object.getOwnPropertyDescriptor(
                            HTMLInputElement.prototype,
                            "value"
                        ).set;
                        setter.call(el, value);
                        el.dispatchEvent(new Event("input", { bubbles: true }));
                        el.dispatchEvent(new Event("change", { bubbles: true }));
                    };

                    setValue(inputs[0], id); // ID
                    setValue(inputs[1], pw); // PW
                }""",
                [naver_id, naver_pw],
            )

            # 로그인 버튼 클릭 (type="button")
            page.locator("button.Button_btn__wNWXt").click()

            # 로그인 성공 판별
            try:
                page.wait_for_url("**/sell.smartstore.naver.com/**", timeout=30000)
            except PlaywrightTimeoutError:
                raise SmartStoreLoginError(
                    "로그인 실패: URL 전환 없음 (캡차/2차 인증 가능성)"
                )

            # 세션 안정화
            page.goto(SMARTSTORE_BASE, wait_until="networkidle")
            cookies = context.cookies()

        finally:
            context.close()
            browser.close()

    if not cookies:
        raise SmartStoreLoginError("로그인 실패: 쿠키 획득 실패")

    # requests.Session으로 쿠키 이관
    session = requests.Session()
    for c in cookies:
        session.cookies.set(
            name=c["name"],
            value=c["value"],
            domain=c.get("domain"),
            path=c.get("path", "/"),
        )

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": SMARTSTORE_BASE,
        "Accept": "application/json, text/plain, */*",
    })

    return session
