import os
import time
import pyautogui
from selenium import webdriver
from selenium.webdriver.common.by import By
import json

from utils import (
    launch_chrome_fullscreen,
    load_points,
    click_point,
    click_and_type,
)
from text_clicker import detect_and_click_text
from order_navigation import load_order_points, perform_actions
from ocr_utils import check_and_input_inventory

# 재고 확인 좌표 (필요시 수정)
INVENTORY_X = 700
INVENTORY_Y = 400


PRODUCT_NAME_SELECTOR = ".product-name"


def save_product_names(driver: webdriver.Chrome, file_path: str = "상품명_목록.txt") -> None:
    """HTML에서 상품명을 추출하여 파일에 저장."""
    elements = driver.find_elements(By.CSS_SELECTOR, PRODUCT_NAME_SELECTOR)
    names = [e.text.strip() for e in elements if e.text.strip()]

    if file_path.endswith(".json"):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(names, f, ensure_ascii=False, indent=2)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            for name in names:
                f.write(name + "\n")
    print(f"✅ 상품명 {len(names)}개 저장 완료 → {file_path}")


def attach_driver() -> webdriver.Chrome:
    """현재 실행 중인 Chrome에 연결."""
    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", "localhost:9222")
    return webdriver.Chrome(options=options)


def main() -> None:
    url = "https://store.bgfretail.com/websrc/deploy/index.html"
    launch_chrome_fullscreen(url)

    login_points = load_points("login_points.json")
    click_and_type(login_points, "id_field.png", "46513", tab_after=True)
    time.sleep(0.5)
    pyautogui.write("1113")
    time.sleep(0.5)
    click_point(login_points, "login_button.png")

    click_point(login_points, "popup_close.png")
    time.sleep(1)
    debug_path = os.path.join(os.path.dirname(__file__), "debug_capture.png")
    pyautogui.screenshot(debug_path)
    print("📸 화면 캡처됨: debug_capture.png")
    detect_and_click_text("발주")

    order_points = load_order_points()
    perform_actions(order_points)

    driver = attach_driver()
    save_product_names(driver)
    driver.quit()
    check_and_input_inventory(INVENTORY_X, INVENTORY_Y)


if __name__ == "__main__":
    main()
