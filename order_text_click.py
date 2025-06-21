import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import pyautogui
import cv2
import numpy as np
import time
from PIL import Image

def detect_and_click_text(target_text, confidence=0.6):
    print(f"🔍 Searching for '{target_text}' on screen...")

    screenshot = pyautogui.screenshot()
    screenshot_np = np.array(screenshot)
    screenshot_rgb = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2RGB)

    data = pytesseract.image_to_data(screenshot_rgb, lang='kor+eng', output_type=pytesseract.Output.DICT)

    for i, word in enumerate(data['text']):
        if word.strip() == "":
            continue
        if target_text in word:
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            center_x = x + w // 2
            center_y = y + h // 2

            print(f"✅ Found '{word}' at ({center_x}, {center_y})")
            pyautogui.moveTo(center_x, center_y)
            time.sleep(0.5)
            pyautogui.click()
            print("🖱️ Clicked on text")
            return True

    print("❌ Target text not found on screen.")
    return False
