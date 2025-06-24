import os
from dotenv import load_dotenv
from playwright.sync_api import Page
from utils import log
from browser.popup_handler_utility import close_layer_popup, setup_dialog_handler

load_dotenv()

URL = "https://store.bgfretail.com/websrc/deploy/index.html"


def perform_login(page: Page, structure: dict) -> bool:
    """Login using credentials from .env and given page structure."""
    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")
    if not user_id or not user_pw:
        log("❗ LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다")
        return False

    log("➡️ 로그인 페이지 접속")
    page.goto(URL)
    page.locator(structure["id"]).click()
    page.keyboard.type(user_id)
    page.locator(structure["password"]).click()
    page.keyboard.type(user_pw)
    page.locator(structure["login_button"]).click()
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_selector("#topMenu", timeout=5000)
    except Exception:
        pass

    if "login" in page.url or not page.locator("#topMenu").is_visible():
        log("❌ 로그인 실패")
        return False

    log("✅ 로그인 성공")
    setup_dialog_handler(page)
    # 선제적으로 알려진 레이어 팝업 처리
    close_layer_popup(page, "#popup", "#popup-close")
    return True
