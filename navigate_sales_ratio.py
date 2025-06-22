import json
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from utils import setup_dialog_handler

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    with open(os.path.join(BASE_DIR, "runtime_config.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def load_structure():
    with open(os.path.join(BASE_DIR, "page_structure.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def find_and_click(page, text: str) -> bool:
    """Search all frames for the given text and click the first match."""
    search_targets = [page] + page.frames
    for target in search_targets:
        locator = target.locator(f"text={text}")
        if locator.count() > 0:
            locator.first.click()
            return True
    return False


def navigate_sales_ratio(page):
    if not find_and_click(page, "매출분석"):
        raise RuntimeError("Cannot find '매출분석' menu")
    page.wait_for_timeout(1000)
    if not find_and_click(page, "중분류별 매출 구성비"):
        raise RuntimeError("Cannot find '중분류별 매출 구성비' submenu")
    page.wait_for_load_state("networkidle")


def run():
    cfg = load_config()
    st = load_structure()

    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")

    if not user_id or not user_pw:
        print("LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다.")
        return

    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    normal_exit = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
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

            for sel in cfg.get("popup_selectors", []):
                if page.locator(sel).count() > 0:
                    page.locator(sel).click()
                    break

            navigate_sales_ratio(page)
            print("메뉴 이동 완료")
            normal_exit = True
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            try:
                browser.close()
            finally:
                print("정상 종료" if normal_exit else "비정상 종료")


if __name__ == "__main__":
    run()
