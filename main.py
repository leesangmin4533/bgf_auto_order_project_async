from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import json
import os


def main() -> None:
    """크롬을 실행해 로그인 후 팝업을 닫는 초기 단계만 수행."""
    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    load_dotenv()
    user_id = os.getenv("BGF_ID")
    user_pw = os.getenv("BGF_PW")

    # ① 브라우저 실행
    driver = webdriver.Chrome()
    driver.get(url)

    # ② 페이지 구조 로드
    with open("page_structure.json", "r", encoding="utf-8") as f:
        structure = json.load(f)

    id_field = structure["id"]
    pw_field = structure["password"]
    login_keyword = structure["login_button"]

    # ③ 로그인 진행 - iframe 전환 없이 직접 입력
    id_elem = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, id_field))
    )
    pw_elem = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, pw_field))
    )
    driver.execute_script("arguments[0].value = arguments[1];", id_elem, user_id)
    driver.execute_script("arguments[0].value = arguments[1];", pw_elem, user_pw)

    login_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, f"[id*='{login_keyword.split(':')[0]}']"))
    )
    driver.execute_script("arguments[0].click();", login_btn)

    # ③ 로그인 후 나타나는 팝업 닫기
    try:
        popup_close = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".popup-close"))
        )
        popup_close.click()
    except Exception:
        print("팝업을 찾을 수 없거나 닫지 못했습니다.")

    # 이후 단계는 추후 구현 예정
    # detect_and_click_text("발주")
    # order_points = load_order_points()
    # perform_actions(order_points)
    # driver.quit()
    # check_and_input_inventory(INVENTORY_X, INVENTORY_Y)


if __name__ == "__main__":
    main()
