import json
import os
from playwright.sync_api import sync_playwright
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        page.locator(st["id"]).click()
        page.keyboard.type(user_id)
        page.locator(st["password"]).click()
        page.keyboard.type(user_pw)
        page.locator(st["login_button"]).click()

        try:
            close_btn = page.locator("[class*='close']")
            if close_btn.count() > 0:
                close_btn.click()
        except Exception as e:
            print(f"경고창 닫기 실패: {e}")

        wait_after_login = cfg.get("wait_after_login", 0)
        if wait_after_login:
            page.wait_for_timeout(wait_after_login * 1000)

        for sel in cfg.get("popup_selectors", []):
            if page.locator(sel).count() > 0:
                page.locator(sel).click()
                break

        browser.close()


if __name__ == "__main__":
    run()
