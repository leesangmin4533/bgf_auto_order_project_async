from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main() -> None:
    """크롬을 실행해 로그인 후 팝업을 닫는 초기 단계만 수행."""
    url = "https://store.bgfretail.com/websrc/deploy/index.html"

    # ① 브라우저 실행
    driver = webdriver.Chrome()
    driver.get(url)

    # ② 로그인 진행 (필요시 셀렉터 수정)
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "loginId"))
    ).send_keys("46513")
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "loginPwd"))
    ).send_keys("1113")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

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
