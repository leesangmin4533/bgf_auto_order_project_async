import datetime
from playwright.sync_api import sync_playwright

import utils
from login.login_handler import perform_login

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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        perform_login(page)

        if not close_popups(page):
            browser.close()
            return

        if datetime.datetime.today().weekday() == 0:
            from sales_analysis.navigate_sales_ratio import navigate_sales_ratio
            navigate_sales_ratio(page)

        browser.close()


if __name__ == "__main__":
    main()
