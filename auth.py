import os
from dotenv import load_dotenv
from playwright.sync_api import Page
from utils import log, handle_exception, wait
from browser.popup_handler_utility import (
    close_layer_popup,
    close_all_popups,
    setup_dialog_handler,
)
from browser.popup_handler import register_dialog_handler

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
        register_dialog_handler(page)
        page.wait_for_timeout(2000)
        login_btn.click()
        page.wait_for_timeout(2000)

        # 로그인 직후 등장하는 재택 안내 팝업 우선 처리
        wait(page)
        close_layer_popup(
            page,
            popup_selector="#popupDiv",
            close_selector="button:has-text('닫기')",
            timeout=3000,
        )
        # 기존 팝업도 추가로 처리
        wait(page)
        close_layer_popup(page, "#popup", "#popup-close")

        # 모든 팝업이 닫힐 때까지 반복적으로 탐색
        wait(page)
        close_all_popups(page)
        wait(page)

        # 로딩 진행 표시가 사라질 때까지 대기
        try:
            page.locator(".progress-container").wait_for(state="hidden", timeout=5000)
        except Exception:
            log("로딩 UI가 사라지지 않음 → 무시하고 다음 진행")

        log("[로그인] 로그인 후 메뉴 로딩 대기")
        try:
            page.wait_for_selector("#topMenu", timeout=10000)
        except Exception:
            log("⚠️ 메뉴 로딩 실패 - #topMenu 미감지")
        else:
            log("✅ 메뉴 로딩 완료")

        log("[로그인] 로그인 성공 판단 완료")
        log("✅ 로그인 성공 → 안정화 대기")
        page.wait_for_timeout(3000)
        setup_dialog_handler(page)
        return True

    except Exception as e:
        handle_exception(page, "perform_login", e)
        return False
