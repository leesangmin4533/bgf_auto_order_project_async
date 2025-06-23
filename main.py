"""메인 자동화 스크립트."""

import json
import os
import glob
import subprocess
import sys
import datetime
from dotenv import load_dotenv
from sales_analysis.navigate_sales_ratio import navigate_sales_ratio
from sales_analysis.extract_sales_detail import extract_sales_detail

# .env 파일 로드
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from utils import (
    setup_dialog_handler,
    close_popups,
    popups_handled,
    process_popups_once,
    close_stzz120_popup,
    inject_init_cleanup_script,
    log,
)


def main() -> None:
    """크롬을 실행해 로그인 후 팝업을 닫는 초기 단계만 수행."""
    log("🚀 자동화 스크립트 시작")
    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    # Load runtime configuration for additional settings
    config_path = os.path.join(BASE_DIR, "runtime_config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        runtime_config = json.load(f)

    # 로그인에 사용할 ID/PW는 .env 파일에서 읽음
    user_id = os.getenv("LOGIN_ID")
    user_pw = os.getenv("LOGIN_PW")

    wait_after_login = runtime_config.get("wait_after_login", 0)
    popup_selectors = runtime_config.get(
        "popup_selectors",
        ["#popupClose", "img[src*='popup_close']"],
    )

    structure_file = os.path.join(BASE_DIR, "page_structure.json")
    if not os.path.exists(structure_file):
        # glob으로 유사한 JSON 파일을 탐색
        matches = glob.glob(os.path.join(BASE_DIR, "*structure*.json"))
        if matches:
            structure_file = matches[0]
            log(f"{structure_file} 파일을 대신 사용합니다.")
        else:
            log(f"{structure_file} 파일을 찾을 수 없습니다. 구조를 자동으로 생성합니다.")
            try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_structure.py")], check=True, cwd=BASE_DIR)
            except Exception as e:
                log(f"구조 파일 생성 실패: {e}")
                return
            if not os.path.exists(structure_file):
                log(f"구조 파일 생성 후에도 {structure_file}을 찾지 못했습니다.")
                return

    try:
        with open(structure_file, "r", encoding="utf-8") as f:
            structure = json.load(f)
    except FileNotFoundError:
        log(f"{structure_file} 파일을 여는 데 실패했습니다. 경로를 확인하세요.")
        return

    # ① Playwright 브라우저 실행
    normal_exit = False
    log("🟡 브라우저 실행")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        inject_init_cleanup_script(page)
        log("✅ 브라우저 페이지 생성 완료")
        setup_dialog_handler(page)
        try:
            log("➡️ 로그인 페이지 접속 중")
            page.goto(url)

            id_field = structure["id"]
            pw_field = structure["password"]
            login_keyword = structure["login_button"]

            if not user_id or not user_pw:
                log("❗ LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다.")
                return
            log("🟡 로그인 시도")
            page.locator(id_field).click()
            page.keyboard.type(user_id)
            page.locator(pw_field).click()
            page.keyboard.type(user_pw)
            page.locator(login_keyword).click()

            if wait_after_login:
                page.wait_for_timeout(wait_after_login * 1000)

            log("🟡 팝업 처리 시작")
            if not process_popups_once(page):
                log("❌ 팝업을 모두 닫지 못해 종료합니다")
                return

            log("🟡 STZZ120 팝업 닫기 시도")
            try:
                close_stzz120_popup(page)
                # 추가 팝업 존재 여부 재확인
                close_popups(page, repeat=4, interval=1000, force=True)
            except Exception as e:
                log(f"❗ STZZ120 팝업 닫기 실패: {e}")

            # 월요일에만 매출 분석 기능 실행
            if datetime.datetime.today().weekday() == 0:
                try:
                    log("➡️ 매출분석 메뉴 진입 시도")
                    navigate_sales_ratio(page)
                    log("✅ 메뉴 진입 성공")
                except Exception as e:
                    log(f"❗ 메뉴 진입 실패 at navigate_sales_ratio: {e}")
                    raise

                try:
                    log("🟡 매출 상세 데이터 추출 시작")
                    extract_sales_detail(page)
                    log("✅ 매출 상세 데이터 추출 완료")
                except Exception as e:
                    log(f"❗ 데이터 추출 실패: {e}")
                    raise

            # ⑤ 정적 HTML 데이터 파싱 예시
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            products = [p.get_text(strip=True) for p in soup.select(".product-name")]
            log(f"상품 목록: {products}")

            normal_exit = True
        except Exception as e:
            log(f"❗ 오류 발생: {e}")
        finally:
            try:
                close_popups(page, force=True)
                browser.close()
            finally:
                log("정상 종료" if normal_exit else "비정상 종료")

    # 이후 단계는 추후 구현 예정
    # detect_and_click_text("발주")
    # order_points = load_order_points()
    # perform_actions(order_points)
    # driver.quit()
    # check_and_input_inventory(INVENTORY_X, INVENTORY_Y)


if __name__ == "__main__":
    main()
