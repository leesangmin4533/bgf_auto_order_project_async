import json
import os
from playwright.sync_api import sync_playwright
from utils import (
    setup_dialog_handler,
    close_popups,
    popups_handled,
    process_popups_once,
    inject_init_cleanup_script,
)
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config() -> dict:
    with open(os.path.join(BASE_DIR, "runtime_config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_structure() -> dict:
    with open(os.path.join(BASE_DIR, "page_structure.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def run() -> None:
    """Run login automation with popup handling."""
    cfg = load_config()
    st = load_structure()

    # ID/PW from environment variables
    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")
    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    if not user_id or not user_pw:
        print("LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다.")
        return

    normal_exit = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        inject_init_cleanup_script(page)
        setup_dialog_handler(page)
        try:
            page.goto(url)

            page.locator(st["id"]).click()
            page.keyboard.type(user_id)
            page.locator(st["password"]).click()
            page.keyboard.type(user_pw)
            page.locator(st["login_button"]).click()

            wait_after_login = cfg.get("wait_after_login", 0)
            if wait_after_login:
                page.wait_for_timeout(wait_after_login * 1000)

            if not process_popups_once(page):
                print("⚠️ 일부 팝업이 닫히지 않았으나 계속 진행합니다")
            else:
                print("✅ 모든 팝업 처리 완료")

            # Additional popup handling for STZZ120 page
            try:
                close_selector = (
                    "#mainframe\\.HFrameSet00\\.VFrameSet00\\.FrameSet\\.WorkFrame\\.STZZ120_P0\\.form\\.btn_close\\:icontext"
                )
                close_btn = page.locator(close_selector)
                if close_btn.count() > 0 and close_btn.is_visible():
                    close_btn.click(timeout=15000)
            except Exception as e:
                print(f"STZZ120 팝업 닫기 실패: {e}")

            normal_exit = True
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            try:
                close_popups(page, force=True)
                browser.close()
            finally:
                print("정상 종료" if normal_exit else "비정상 종료")


if __name__ == "__main__":
    run()
