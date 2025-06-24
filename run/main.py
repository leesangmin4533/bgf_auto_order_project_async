"""Main orchestration script."""

import json
import os
import glob
import subprocess
import sys
import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from utils import (
    inject_init_cleanup_script,
    set_ignore_popup_failure,
    log,
    update_instruction_state,
)
from browser.popup_handler_utility import (
    setup_dialog_handler,
    close_all_popups,
)
from browser.popup_handler import (
    dialog_blocked,
    login_page_visible,
)
from auth import perform_login
from order import run_sales_analysis

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)


def load_structure() -> dict:
    structure_file = os.path.join(ROOT_DIR, "config", "page_structure.json")
    if not os.path.exists(structure_file):
        matches = glob.glob(os.path.join(BASE_DIR, "*structure*.json"))
        if matches:
            structure_file = matches[0]
            log(f"{structure_file} 파일을 대신 사용합니다.")
        else:
            log(f"{structure_file} 파일을 찾을 수 없습니다. 구조를 자동으로 생성합니다.")
            subprocess.run([sys.executable, os.path.join(ROOT_DIR, "core", "build_structure.py")], check=True, cwd=ROOT_DIR)
    with open(structure_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    cfg_path = os.path.join(ROOT_DIR, "config", "runtime_config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    log("🚀 자동화 시작")
    update_instruction_state("로그인 시도")
    structure = load_structure()
    config = load_config()
    wait_after_login = config.get("wait_after_login", 0)
    set_ignore_popup_failure(config.get("ignore_popup_failure", False))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        inject_init_cleanup_script(page)
        setup_dialog_handler(page)
        normal_exit = False
        try:
            if not perform_login(page, structure):
                update_instruction_state("종료", "로그인 실패")
                return
            if wait_after_login:
                page.wait_for_timeout(wait_after_login * 1000)
            update_instruction_state("팝업 처리 중")
            if not close_all_popups(page):
                update_instruction_state("종료", "popup 닫기 실패")
                return
            if dialog_blocked(page) or login_page_visible(page):
                update_instruction_state("종료", "차단 메시지 감지")
                return
            update_instruction_state("메뉴 진입")
            run_sales_analysis(page)
            normal_exit = True
            update_instruction_state("완료")
        except Exception as e:
            log(f"❗ 오류 발생: {e}")
            update_instruction_state("종료", str(e))
        finally:
            try:
                browser.close()
            finally:
                log("정상 종료" if normal_exit else "비정상 종료")


if __name__ == "__main__":
    main()
