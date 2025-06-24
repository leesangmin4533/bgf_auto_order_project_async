import os
from dotenv import load_dotenv
from playwright.sync_api import Page
from utils import log, handle_exception
from browser.popup_handler_utility import close_layer_popup, setup_dialog_handler

load_dotenv()

URL = "https://store.bgfretail.com/websrc/deploy/index.html"


def perform_login(page: Page, structure: dict) -> bool:
    """Login using credentials from .env and given page structure."""
    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")
    if not user_id or not user_pw:
        log("❗ LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다", stage="로그인")
        return False

    try:
        log("[로그인] 입력값 채우기")
        page.goto(URL)
        page.fill(structure["id"], user_id)
        page.fill(structure["password"], user_pw)

        log("[로그인] 로그인 버튼 클릭")
        page.click(structure["login_button"])

        log("[로그인] 로그인 후 로딩 대기")
        page.wait_for_selector("#topMenu", timeout=5000)

        log("[로그인] 로그인 성공 판단 완료")
        setup_dialog_handler(page)
        close_layer_popup(page, "#popup", "#popup-close")
        return True

    except Exception as e:
        handle_exception(page, "perform_login", e)
        return False
