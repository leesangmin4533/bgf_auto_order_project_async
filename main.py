"""메인 자동화 스크립트."""

import json
import os
import glob
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def main() -> None:
    """크롬을 실행해 로그인 후 팝업을 닫는 초기 단계만 수행."""
    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    load_dotenv(os.path.join(BASE_DIR, '.env'))
    user_id = os.getenv("BGF_ID")
    user_pw = os.getenv("BGF_PW")

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
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)

        # ② 페이지 구조 로드 완료 후 로그인 진행

        id_field = structure["id"]
        pw_field = structure["password"]
        login_keyword = structure["login_button"]

        # ③ 로그인 진행
        if not user_id:
            raise ValueError("user_id가 설정되지 않았습니다.")
        page.fill(f"#{id_field}", user_id)
        page.fill(f"#{pw_field}", user_pw)
        page.click(f"#{login_keyword}")

        # ④ 로그인 후 나타나는 팝업 닫기
        try:
            page.click(".popup-close")
        except Exception:
            print("팝업을 찾을 수 없거나 닫지 못했습니다.")

        # ⑤ 정적 HTML 데이터 파싱 예시
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        products = [p.get_text(strip=True) for p in soup.select(".product-name")]
        print("상품 목록:", products)

        browser.close()

    # 이후 단계는 추후 구현 예정
    # detect_and_click_text("발주")
    # order_points = load_order_points()
    # perform_actions(order_points)
    # driver.quit()
    # check_and_input_inventory(INVENTORY_X, INVENTORY_Y)


if __name__ == "__main__":
    main()
