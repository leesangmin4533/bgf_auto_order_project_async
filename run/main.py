"""Simple login script."""

import os
import json
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from auth import perform_login
from utils import inject_init_cleanup_script, log, wait

load_dotenv()

STRUCTURE_PATH = os.path.join(PROJECT_ROOT, "config", "page_structure.json")


def load_structure() -> dict:
    with open(STRUCTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    structure = load_structure()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        inject_init_cleanup_script(page)
        success = perform_login(page, structure)
        wait(page)
        log("로그인 성공" if success else "로그인 실패", stage="결과")
        browser.close()


if __name__ == "__main__":
    main()
