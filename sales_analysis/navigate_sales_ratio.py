import json
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect
from utils import (
    inject_init_cleanup_script,
    popups_handled,
    log,
    wait,
)
from browser.popup_handler import setup_dialog_handler
from browser.popup_handler_utility import close_all_popups_event


def click_sales_analysis_tab(page) -> bool:
    """Click the '매출분석' tab in the top menu."""
    selector = "div.nexatextitem:has-text('매출분석')"
    try:
        element = page.wait_for_selector(selector, timeout=5000)
        wait(page)
        element.click()
        wait(page)
        log("'매출분석' 탭 클릭 성공")
        return True
    except Exception as e:
        log(f"'매출분석' 탭 클릭 실패: {e}")
        return False

load_dotenv()

# 프로젝트 루트 디렉터리 경로
BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR


def load_config():
    config_path = ROOT_DIR / "config" / "runtime_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_structure():
    structure_path = ROOT_DIR / "config" / "page_structure.json"
    with open(structure_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_and_click(page, text: str) -> bool:
    """Search all frames for the given text and click the first match."""
    search_targets = [page] + page.frames
    for target in search_targets:
        locator = target.locator(f"text={text}")
        if locator.count() > 0:
            wait(page)
            locator.first.click()
            wait(page)
            return True
    return False


def navigate_sales_ratio(page):
    if not popups_handled():
        raise RuntimeError("팝업 처리가 완료되지 않아 메뉴 이동을 중단합니다")
    wait(page)
    if not click_sales_analysis_tab(page):
        raise RuntimeError("Cannot find '매출분석' menu")
    wait(page)
    expect(page.locator("text=중분류별 매출 구성비")).to_be_visible(timeout=5000)
    if not find_and_click(page, "중분류별 매출 구성비"):
        raise RuntimeError("Cannot find '중분류별 매출 구성비' submenu")
    wait(page)
    page.wait_for_load_state("networkidle")
    wait(page)


def run():
    cfg = load_config()
    st = load_structure()

    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")

    if not user_id or not user_pw:
        log("LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다.")
        return

    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    normal_exit = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        inject_init_cleanup_script(page)
        setup_dialog_handler(page)
        try:
            wait(page)
            page.goto(url)
            wait(page)

            page.locator(st["id"]).click()
            wait(page)
            page.keyboard.type(user_id)
            wait(page)
            page.locator(st["password"]).click()
            wait(page)
            page.keyboard.type(user_pw)
            wait(page)
            page.locator(st["login_button"]).click()
            wait(page)

            wait_after_login = cfg.get("wait_after_login", 0)
            if wait_after_login:
                page.wait_for_timeout(wait_after_login * 1000)
            wait(page)

            if not popups_handled():
                if not close_all_popups_event(page):
                    log("❗ 팝업을 모두 닫지 못해 작업을 중단합니다")
                    return
            wait(page)

            navigate_sales_ratio(page)
            log("메뉴 이동 완료")
            normal_exit = True
        except Exception as e:
            log(f"오류 발생: {e}")
        finally:
            try:
                browser.close()
            finally:
                log("정상 종료" if normal_exit else "비정상 종료")


if __name__ == "__main__":
    run()
