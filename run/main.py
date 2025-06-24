"""Main orchestration script."""

import datetime
import glob
import json
import os
import subprocess
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from auth import perform_login
from browser.popup_handler import dialog_blocked, is_logged_in
from browser.popup_handler_utility import close_all_popups, setup_dialog_handler
from order import run_sales_analysis
from utils import (
    fallback_close_popups,
    inject_init_cleanup_script,
    log,
    set_ignore_popup_failure,
    update_instruction_state,
    handle_exception,
    wait,
)

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
            log(
                f"{structure_file} 파일을 찾을 수 없습니다. 구조를 자동으로 생성합니다."
            )
            subprocess.run(
                [sys.executable, os.path.join(ROOT_DIR, "core", "build_structure.py")],
                check=True,
                cwd=ROOT_DIR,
            )
    with open(structure_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    cfg_path = os.path.join(ROOT_DIR, "config", "runtime_config.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    log("🚀 자동화 시작", stage="시작")
    update_instruction_state("로그인 시도")
    structure = load_structure()
    config = load_config()
    wait_after_login = config.get("wait_after_login", 0)
    set_ignore_popup_failure(config.get("ignore_popup_failure", False))
    popup_fail_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        inject_init_cleanup_script(page)
        setup_dialog_handler(page)
        normal_exit = False
        try:
            log("[로그인 단계] ➡️ perform_login() 호출")
            if not perform_login(page, structure):
                log("[로그인 단계] ❌ perform_login 실패 → 로그인 종료")
                update_instruction_state("종료", "로그인 실패")
                return

            wait(page)

            update_instruction_state("팝업 처리 중")
            log("close_all_popups() 호출", stage="팝업 처리")
            wait(page)
            try:
                popup_closed = close_all_popups(page)
                wait(page)
                if not popup_closed:
                    popup_fail_count += 1
                    log("❌ 팝업 닫기 실패", stage="팝업 처리")
                    # 추가 닫기 버튼 탐색 시도
                    alt_selectors = [
                        "div:has-text('닫기')",
                        "button:has-text('닫기')",
                        "a:has-text('닫기')",
                        "[class*='close']",
                        "[id*='close']",
                    ]
                    alt_found = False
                    for sel in alt_selectors:
                        try:
                            locs = page.locator(sel)
                        except Exception:
                            continue
                        for i in range(locs.count()):
                            btn = locs.nth(i)
                            if btn.is_visible():
                                try:
                                    btn.click(timeout=0)
                                    alt_found = True
                                except Exception:
                                    continue
                        if alt_found:
                            break
                    if alt_found and close_all_popups(page):
                        popup_closed = True
                        wait(page)
                    if not popup_closed:
                        # 메뉴 탐색 재시도
                        menu_found = False
                        for _ in range(3):
                            try:
                                page.wait_for_selector("#topMenu", timeout=3000)
                                menu_found = True
                                break
                            except Exception:
                                page.wait_for_timeout(1000)
                        if not menu_found:
                            update_instruction_state("종료", "팝업 처리 실패")
                            if popup_fail_count >= 2:
                                try:
                                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                    with open(f"popup_fail_{ts}.html", "w", encoding="utf-8") as f:
                                        f.write(page.content())
                                    log(f"📄 페이지 HTML 저장됨: popup_fail_{ts}.html")
                                except Exception as se:
                                    log(f"페이지 저장 실패: {se}")
                            return
                    if popup_fail_count >= 3:
                        fallback_close_popups(page)
                        popup_fail_count = 0
            except Exception as e:
                handle_exception(page, "팝업처리", e)
                update_instruction_state("종료", "팝업 처리 중 예외")
                return

            page.wait_for_timeout(2000)
            try:
                page.wait_for_selector("#topMenu", timeout=10000)
            except Exception as e:
                log("⚠️ 메뉴 로딩 실패 - #topMenu 미감지", stage="로그인후요소")
                handle_exception(page, "로그인후요소", e)
            else:
                log("✅ 메뉴 로딩 완료", stage="로그인후요소")

            page.wait_for_timeout(max(1000, wait_after_login * 1000))

            if not is_logged_in(page):
                update_instruction_state("종료", "로그인 후 요소 확인 실패")
                return
            if dialog_blocked(page):
                update_instruction_state("종료", "차단 메시지 감지")
                return
            update_instruction_state("메뉴 진입")
            try:
                run_sales_analysis(page)
            except Exception as e:
                handle_exception(page, "메뉴진입", e)
                update_instruction_state("종료", "메뉴 이동 중 예외")
                return
            normal_exit = True
            update_instruction_state("완료")
        except Exception as e:
            handle_exception(page, "메인", e)
            update_instruction_state("종료", str(e))
        finally:
            try:
                browser.close()
            finally:
                log("정상 종료" if normal_exit else "비정상 종료")


if __name__ == "__main__":
    main()
