import os
import time
import cv2
import numpy as np
import pyautogui
import pytesseract

from utils import (
    TESSERACT_CMD,
    launch_chrome_fullscreen,
    load_points,
    click_point,
    click_and_type,
)
from text_clicker import detect_and_click_text
from order_navigation import load_order_points, perform_actions
from ocr_utils import check_and_input_inventory

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# 재고 확인 좌표 (필요시 수정)
INVENTORY_X = 700
INVENTORY_Y = 400


def save_fullscreen_ocr_debug() -> None:
    """전체 화면을 OCR 처리하여 디버그 용도로 저장."""
    full_image = pyautogui.screenshot()
    full_image_np = np.array(full_image)
    gray = cv2.cvtColor(full_image_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    debug_dir = os.path.join(os.path.dirname(__file__), "ocr_debug")
    os.makedirs(debug_dir, exist_ok=True)
    cv2.imwrite(os.path.join(debug_dir, "상품명_전체화면.png"), thresh)

    data = pytesseract.image_to_data(
        thresh, lang="kor+eng", output_type=pytesseract.Output.DICT
    )
    with open(os.path.join(debug_dir, "상품명_목록.txt"), "w", encoding="utf-8") as f:
        for word in data["text"]:
            if word.strip():
                f.write(word.strip() + "\n")
    print("📸 상품명 전체화면 및 텍스트 목록 저장 완료")


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

    save_fullscreen_ocr_debug()
    check_and_input_inventory(INVENTORY_X, INVENTORY_Y)


if __name__ == "__main__":
    main()
