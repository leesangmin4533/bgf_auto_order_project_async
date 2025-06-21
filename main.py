import pytesseract
import pyautogui
from PIL import Image
import cv2
import numpy as np
import time
import os

# Tesseract 설치 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 재고 셀 위치 (정확한 좌표로 수정 필요)
INVENTORY_X = 700
INVENTORY_Y = 400

# OCR 영역 저장 디버깅 이미지 경로
BASE_DIR = os.path.dirname(__file__)
OCR_DEBUG_FOLDER = os.path.join(BASE_DIR, "ocr_debug")
os.makedirs(OCR_DEBUG_FOLDER, exist_ok=True)
DEBUG_OCR_IMAGE = os.path.join(OCR_DEBUG_FOLDER, "debug_ocr.png")

def capture_inventory_cell(x, y, w=80, h=40):
    left = x - w // 2
    top = y - h // 2
    screenshot = pyautogui.screenshot(region=(left, top, w, h))
    return screenshot

def extract_text_from_image(image):
    # 이미지 확대 및 처리
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    _, thresh = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY)

    # 디버깅용 이미지 저장
    success = cv2.imwrite(DEBUG_OCR_IMAGE, thresh)
    if success:
        print(f"🖼️ OCR 디버그 이미지 저장됨: {DEBUG_OCR_IMAGE}")
    else:
        print("⚠️ OCR 이미지 저장 실패")

    text = pytesseract.image_to_string(thresh, config='--psm 7 digits').strip()
    return text

def check_and_input_inventory(x, y):
    print("🔍 재고 영역 OCR 시작...")
    image = capture_inventory_cell(x, y)
    text = extract_text_from_image(image)
    print(f"📦 OCR 결과: '{text}'")
    if text == "0":
        pyautogui.click(x, y)
        time.sleep(0.2)
        pyautogui.write("1")
        pyautogui.press("enter")
        print("✅ 재고 0 → '1' 입력 완료")
    else:
        print("⏭️ 입력 조건 불충족 (재고 0 아님)")

import subprocess
import time
import pygetwindow as gw
import pyautogui
import json
import os

from order_text_click import detect_and_click_text

CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
USER_DATA_DIR = "C:\\Users\\kanur\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_NAME = "Default"
POINTS_FILE = os.path.join(os.path.dirname(__file__), "login_points.json")

def launch_chrome_fullscreen(url):
    subprocess.Popen([
        CHROME_PATH,
        f'--user-data-dir={USER_DATA_DIR}',
        f'--profile-directory={PROFILE_NAME}',
        '--new-window',
        '--kiosk',
        url
    ])
    print("✅ 크롬 전체화면 실행됨")
    time.sleep(3)

def get_chrome_window_position():
    time.sleep(1)
    windows = gw.getWindowsWithTitle("Chrome")
    if not windows:
        raise Exception("❌ Chrome 창을 찾을 수 없습니다.")
    win = windows[0]
    return win.left, win.top

def click_using_saved_points(point_key):
    with open(POINTS_FILE, "r", encoding="utf-8") as f:
        points = json.load(f)
    if point_key not in points:
        print(f"⚠️ 포인트 {point_key} 없음")
        return
    base_x, base_y = get_chrome_window_position()
    x = base_x + points[point_key]["x"]
    y = base_y + points[point_key]["y"]
    print(f"🔴 마우스 이동 예정 → ({x}, {y})")
    pyautogui.moveTo(x, y)
    time.sleep(1)
    pyautogui.click()
    print(f"🖱️ {point_key} 클릭됨 → 실제 좌표: ({x}, {y})")
    time.sleep(0.5)

def click_and_type(point_key, text=None, tab_after=False):
    with open(POINTS_FILE, "r", encoding="utf-8") as f:
        points = json.load(f)
    if point_key not in points:
        raise KeyError(f"{point_key} 좌표가 저장되어 있지 않습니다.")
    base_x, base_y = get_chrome_window_position()
    x = base_x + points[point_key]["x"]
    y = base_y + points[point_key]["y"]
    pyautogui.moveTo(x, y)
    time.sleep(0.3)
    pyautogui.click()
    print(f"🖱️ {point_key} 클릭됨 → 실제 좌표: ({x}, {y})")
    time.sleep(0.5)
    if text:
        pyautogui.write(text)
        print(f"⌨️ 입력됨: {text}")
    if tab_after:
        pyautogui.press('tab')
        print("➡️ 탭키 전환됨")

def main():
    url = "https://store.bgfretail.com/websrc/deploy/index.html"
    launch_chrome_fullscreen(url)

    click_and_type("id_field.png", "46513", tab_after=True)
    time.sleep(0.5)
    pyautogui.write("1113")
    time.sleep(0.5)
    click_using_saved_points("login_button.png")

    click_using_saved_points("popup_close.png")
    time.sleep(1)
    debug_path = os.path.join(os.path.dirname(__file__), "debug_capture.png")
    pyautogui.screenshot(debug_path)
    print("📸 화면 캡처됨: debug_capture.png")
    detect_and_click_text("발주")

    subprocess.run(['python', 'C:/Users/kanur/OneDrive/바탕 화면/자동발주/a/order_navigation_fixed.py'], check=False)

    full_image = pyautogui.screenshot()
    full_image_np = np.array(full_image)
    gray = cv2.cvtColor(full_image_np, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
    ocr_debug_path = r"C:\\Users\\kanur\\OneDrive\\바탕 화면\\자동발주\\a\\ocr_debug"
    cv2.imwrite(os.path.join(ocr_debug_path, "상품명_전체화면.png"), thresh)

    data = pytesseract.image_to_data(thresh, lang="kor+eng", output_type=pytesseract.Output.DICT)
    with open(os.path.join(ocr_debug_path, "상품명_목록.txt"), "w", encoding="utf-8") as f:
        for word in data["text"]:
            if word.strip():
                f.write(word.strip() + "\n")
    print("📸 상품명 전체화면 및 텍스트 목록 저장 완료")
    check_and_input_inventory(INVENTORY_X, INVENTORY_Y)

if __name__ == "__main__":
    main()
