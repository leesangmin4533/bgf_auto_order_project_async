import os
from playwright.sync_api import Page
from dotenv import load_dotenv
from popup_handler import is_logged_in
from common import log

load_dotenv()
ID = os.getenv("LOGIN_ID")
PW = os.getenv("LOGIN_PW")


def perform_login(page: Page) -> bool:
    """Login using credentials from ``.env``.

    Returns
    -------
    bool
        ``True`` on successful login, ``False`` otherwise.
    """
    page.goto("https://store.bgfretail.com/websrc/deploy/index.html")

    page.wait_for_selector(
        "#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_id\\:input",
        timeout=10000,
    )
    page.fill(
        "#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_id\\:input",
        ID,
    )
    page.wait_for_timeout(1000)

    page.fill(
        "#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_pw\\:input",
        PW,
    )
    page.wait_for_timeout(1000)

    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    if is_logged_in(page):
        log("✅ 로그인 성공")
        return True
    else:
        log("❌ 로그인 실패")
        return False
