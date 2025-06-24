import os
import time
import cv2
import numpy as np
import pytesseract
import pyautogui

from utils import TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

BASE_DIR = os.path.dirname(__file__)
OCR_DEBUG_FOLDER = os.path.join(BASE_DIR, "ocr_debug")
os.makedirs(OCR_DEBUG_FOLDER, exist_ok=True)


def capture_region(x: int, y: int, w: int = 80, h: int = 40):
    """주어진 영역을 캡처."""
    left = x - w // 2
    top = y - h // 2
    return pyautogui.screenshot(region=(left, top, w, h))


def extract_text(image, debug_name: str = "debug_ocr.png") -> str:
    """OCR을 통해 이미지에서 텍스트 추출."""
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    _, thresh = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY)
    debug_path = os.path.join(OCR_DEBUG_FOLDER, debug_name)
    if cv2.imwrite(debug_path, thresh):
        print(f"🖼️ OCR 디버그 이미지 저장됨: {debug_path}")
    else:
        print("⚠️ OCR 이미지 저장 실패")
    return pytesseract.image_to_string(thresh, config='--psm 7 digits').strip()


def check_and_input_inventory(x: int, y: int) -> None:
    """재고가 0인 경우 1을 입력."""
    print("🔍 재고 영역 OCR 시작...")
    image = capture_region(x, y)
    text = extract_text(image)
    print(f"📦 OCR 결과: '{text}'")
    if text == "0":
        pyautogui.click(x, y)
        time.sleep(0.2)
        pyautogui.write("1")
        pyautogui.press("enter")
        print("✅ 재고 0 → '1' 입력 완료")
    else:
        print("⏭️ 입력 조건 불충족 (재고 0 아님)")
