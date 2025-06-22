"""메인 자동화 스크립트."""

import json
import os
import glob
import subprocess
import sys
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from utils import setup_dialog_handler, close_popups


def main() -> None:
    """크롬을 실행해 로그인 후 팝업을 닫는 초기 단계만 수행."""
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
            print(f"{structure_file} 파일을 대신 사용합니다.")
        else:
            print(f"{structure_file} 파일을 찾을 수 없습니다. 구조를 자동으로 생성합니다.")
            try:
                subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_structure.py")], check=True, cwd=BASE_DIR)
            except Exception as e:
                print(f"구조 파일 생성 실패: {e}")
                return
            if not os.path.exists(structure_file):
                print(f"구조 파일 생성 후에도 {structure_file}을 찾지 못했습니다.")
                return

    try:
        with open(structure_file, "r", encoding="utf-8") as f:
            structure = json.load(f)
    except FileNotFoundError:
        print(f"{structure_file} 파일을 여는 데 실패했습니다. 경로를 확인하세요.")
        return

    # ① Playwright 브라우저 실행
    normal_exit = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        setup_dialog_handler(page)
        try:
            page.goto(url)

            # ② 페이지 구조 로드 완료 후 로그인 진행

            id_field = structure["id"]
            pw_field = structure["password"]
            login_keyword = structure["login_button"]

            # ③ 로그인 진행
            if not user_id or not user_pw:
                print("LOGIN_ID 또는 LOGIN_PW가 설정되지 않았습니다.")
                return
            page.locator(id_field).click()
            page.keyboard.type(user_id)
            page.locator(pw_field).click()
            page.keyboard.type(user_pw)
            page.locator(login_keyword).click()

            if wait_after_login:
                page.wait_for_timeout(wait_after_login * 1000)

            # ④ 로그인 후 나타나는 팝업 닫기
            print("팝업 감지 여부")
            clicked = False
            for sel in popup_selectors:
                if page.locator(sel).count() > 0:
                    page.locator(sel).click()
                    clicked = True
                    break
            if clicked:
                print("닫기 버튼 클릭 완료")
            else:
                print("버튼 없음")

            # STZZ120 페이지 팝업 닫기 처리
            try:
                close_selector = (
                    "#mainframe\\.HFrameSet00\\.VFrameSet00\\.FrameSet\\.WorkFrame\\.STZZ120_P0\\.form\\.btn_close\\:icontext"
                )
                close_btn = page.locator(close_selector)
                if close_btn.count() > 0 and close_btn.is_visible():
                    close_btn.click()
            except Exception as e:
                print(f"STZZ120 팝업 닫기 실패: {e}")

            # ⑤ 정적 HTML 데이터 파싱 예시
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            products = [p.get_text(strip=True) for p in soup.select(".product-name")]
            print("상품 목록:", products)

            normal_exit = True
        except Exception as e:
            print(f"오류 발생: {e}")
        finally:
            try:
                close_popups(page)
                browser.close()
            finally:
                print("정상 종료" if normal_exit else "비정상 종료")

    # 이후 단계는 추후 구현 예정
    # detect_and_click_text("발주")
    # order_points = load_order_points()
    # perform_actions(order_points)
    # driver.quit()
    # check_and_input_inventory(INVENTORY_X, INVENTORY_Y)


if __name__ == "__main__":
    main()
