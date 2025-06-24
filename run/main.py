import json
import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STRUCTURE_PATH = PROJECT_ROOT / "config" / "page_structure.json"
URL = "https://store.bgfretail.com/websrc/deploy/index.html"


def load_structure() -> dict:
    with open(STRUCTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    structure = load_structure()
    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(URL)
        page.fill(structure["id"], user_id)
        page.fill(structure["password"], user_pw)
        page.click(structure["login_button"])
        page.wait_for_timeout(5000)
        browser.close()


if __name__ == "__main__":
    main()
