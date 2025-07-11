import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure the project root is in the module search path so "login" package is found
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from login import perform_login
from common import process_popups_once, popups_handled
from order import run_sales_analysis


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        if not perform_login(page):
            browser.close()
            return

        if not process_popups_once(page):
            browser.close()
            return

        if popups_handled() and datetime.datetime.today().weekday() == 0:
            run_sales_analysis(page)

        browser.close()


if __name__ == "__main__":
    main()
