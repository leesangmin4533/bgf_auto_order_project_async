import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import utils

load_dotenv()

ID = os.getenv("LOGIN_ID")
PW = os.getenv("LOGIN_PW")


POPUPS_CLOSED = False


def close_popups(page, loops: int = 2) -> bool:
    """Close visible popups by searching common close buttons."""
    global POPUPS_CLOSED
    if POPUPS_CLOSED:
        utils.popup_handled = True
        return True

    selectors = [
        "text=닫기",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='close']",
        "[id*='close']",
    ]

    for _ in range(max(2, loops)):
        found = False
        for sel in selectors:
            try:
                locs = page.locator(sel)
                for i in range(locs.count()):
                    btn = locs.nth(i)
                    if btn.is_visible():
                        try:
                            btn.click(timeout=0)
                            page.wait_for_timeout(500)
                            found = True
                        except Exception:
                            pass
            except Exception:
                pass
        if not found:
            break
        page.wait_for_timeout(1000)

    for sel in selectors:
        try:
            locs = page.locator(sel)
            for i in range(locs.count()):
                if locs.nth(i).is_visible():
                    POPUPS_CLOSED = False
                    utils.popup_handled = False
                    return False
        except Exception:
            continue

    POPUPS_CLOSED = True
    utils.popup_handled = True
    return True


def main():
    import datetime
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
            nav = __import__(
                "sales_analysis.navigate_sales_ratio",
                fromlist=["navigate_sales_ratio"],
            )
            nav.navigate_sales_ratio(page)

        browser.close()


if __name__ == "__main__":
    main()
