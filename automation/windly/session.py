import time
from playwright.sync_api import sync_playwright

WINDLY_LOGIN_URL = "https://hub.windly.cc/accounts/login"

class WindlySession:
    def __init__(self, user_id, user_pw):
        self.user_id = user_id
        self.user_pw = user_pw
        self.p = None
        self.browser = None
        self.page = None

    def start(self):
        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch(headless=False)
        self.page = self.browser.new_page()
        return self.page

    def login(self):
        self.page.goto(WINDLY_LOGIN_URL)
        self.page.fill("input[name='email']", self.user_id)
        self.page.fill("input[name='password']", self.user_pw)
        self.page.click("button[type='submit']")
        time.sleep(2)

    def close(self):
        try:
            if self.page: self.page.close()
            if self.browser: self.browser.close()
            if self.p: self.p.stop()
        except:
            pass
