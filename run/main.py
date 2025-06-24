import os
import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from browser.popup_handler_utility import close_all_popups_event
from sales_analysis.navigate_sales_ratio import navigate_sales_ratio
from utils import popups_handled

load_dotenv()

ID = os.getenv("LOGIN_ID")
PW = os.getenv("LOGIN_PW")


def close_popups(page) -> bool:
    """Attempt to close all popups using multiple search passes."""
    if popups_handled():
        return True
    success = close_all_popups_event(page, loops=3, wait_ms=1000)
    return success and popups_handled()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto("https://store.bgfretail.com/websrc/deploy/index.html")

        # 아이디 입력
        page.fill("#txtUserID", ID)
        page.wait_for_timeout(1000)

        # 비밀번호 입력
        page.fill("#txtPassWord", PW)
        page.wait_for_timeout(1000)

        # 로그인 버튼 클릭
        page.click("#btnLogin")

        # 로그인 결과 확인을 위해 5초 대기
        page.wait_for_timeout(5000)

        if not close_popups(page):
            browser.close()
            return

        if datetime.datetime.today().weekday() == 0:
            navigate_sales_ratio(page)

        browser.close()


if __name__ == "__main__":
    main()
