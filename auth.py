import os
from dotenv import load_dotenv
from playwright.sync_api import Page
from utils import log, handle_exception, wait

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
        wait(page)
        page.goto(URL)
        wait(page)

        # Wait for both input fields to be ready
        page.wait_for_selector(structure["id"])
        page.wait_for_selector(structure["password"])

        id_input = page.locator(structure["id"])
        pw_input = page.locator(structure["password"])

        log("[로그인] 아이디 입력")
        wait(page)
        id_input.click()
        wait(page)
        id_input.fill(user_id)
        wait(page)

        log("[로그인] 비밀번호 입력")
        wait(page)
        pw_input.click()
        wait(page)
        pw_input.fill(user_pw)
        wait(page)

        # Small delay before clicking the login button
        wait(page)

        login_btn = page.locator(structure["login_button"])
        log("[로그인] 로그인 버튼 클릭")
        wait(page)
        login_btn.click()
        page.wait_for_timeout(3000)

        log("[로그인] 로그인 결과 확인")
        try:
            page.wait_for_selector("#topMenu", timeout=10000)
        except Exception:
            log("⚠️ 메뉴 로딩 실패 - #topMenu 미감지")
            return False
        else:
            log("✅ 로그인 성공")
            return True

    except Exception as e:
        handle_exception(page, "perform_login", e)
        return False
