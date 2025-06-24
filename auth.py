import os
import datetime
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
        log("[로그인] 페이지 이동")
        page.goto(URL)

        # Wait for both input fields to be ready
        page.wait_for_selector(structure["id"])
        page.wait_for_selector(structure["password"])

        id_input = page.locator(structure["id"])
        pw_input = page.locator(structure["password"])

        log("[로그인] 아이디 입력")
        id_input.click()
        id_input.fill(user_id)

        log("[로그인] 비밀번호 입력")
        pw_input.click()
        pw_input.fill(user_pw)

        # Small delay before clicking the login button
        page.wait_for_timeout(500)

        login_btn = page.locator(structure["login_button"])
        log("[로그인] 로그인 버튼 클릭")
        login_btn.click()

        # Close the '재택 유선권장 안내' layer popup that appears right after login
        closed = False
        for _ in range(2):
            closed = close_layer_popup(
                page,
                popup_selector=".el-dialog",
                close_selector="button:has-text('닫기')",
            )
            if closed:
                break
        if not closed:
            log("❌ 레이어 팝업 닫기 실패", stage="팝업 처리")
            try:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                page.screenshot(path=f"screenshots/popup_close_fail_{ts}.png")
            except Exception:
                pass

        log("[로그인] 로그인 후 로딩 대기")
        page.wait_for_selector("#topMenu", timeout=5000)

        log("[로그인] 로그인 성공 판단 완료")
        setup_dialog_handler(page)
        return True

    except Exception as e:
        handle_exception(page, "perform_login", e)
        return False
