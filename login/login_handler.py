import os
from playwright.sync_api import Page
from dotenv import load_dotenv

load_dotenv()
ID = os.getenv("LOGIN_ID")
PW = os.getenv("LOGIN_PW")


def perform_login(page: Page):
    page.goto("https://store.bgfretail.com/websrc/deploy/index.html")

    page.wait_for_selector("#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_id\\:input", timeout=10000)
    page.fill("#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_id\\:input", ID)
    page.wait_for_timeout(1000)

    page.fill("#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_pw\\:input", PW)
    page.wait_for_timeout(1000)

    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
