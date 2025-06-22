import os
import json
import time
import subprocess
import pyautogui
import pygetwindow as gw

# 공통 설정 및 유틸리티 함수 모음
TESSERACT_CMD = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
CHROME_PATH = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
USER_DATA_DIR = r"C:\\Users\\kanur\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_NAME = "Default"


def launch_chrome_fullscreen(url: str) -> None:
    """지정한 URL을 전체화면 모드로 크롬에서 실행."""
    subprocess.Popen([
        CHROME_PATH,
        f"--user-data-dir={USER_DATA_DIR}",
        f"--profile-directory={PROFILE_NAME}",
        "--remote-debugging-port=9222",
        "--new-window",
        "--kiosk",
        url,
    ])
    print("✅ 크롬 전체화면 실행됨")
    time.sleep(3)


def get_chrome_window_position() -> tuple[int, int]:
    """Chrome 창의 위치를 반환."""
    time.sleep(1)
    windows = gw.getWindowsWithTitle("Chrome")
    if not windows:
        raise RuntimeError("❌ Chrome 창을 찾을 수 없습니다.")
    win = windows[0]
    return win.left, win.top


def load_points(file_name: str) -> dict:
    """포인트 정보 JSON을 로드."""
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def click_point(points: dict, point_key: str) -> tuple[int, int]:
    """저장된 좌표를 기준으로 클릭 후 실제 좌표를 반환."""
    if point_key not in points:
        raise KeyError(f"{point_key} 좌표가 저장되어 있지 않습니다.")
    base_x, base_y = get_chrome_window_position()
    x = base_x + points[point_key]["x"]
    y = base_y + points[point_key]["y"]
    pyautogui.moveTo(x, y)
    time.sleep(0.5)
    pyautogui.click()
    print(f"🖱️ {point_key} 클릭됨 → 실제 좌표: ({x}, {y})")
    time.sleep(0.5)
    return x, y


def click_and_type(points: dict, point_key: str, text: str | None = None, tab_after: bool = False) -> tuple[int, int]:
    """클릭 후 텍스트 입력 및 탭 이동."""
    x, y = click_point(points, point_key)
    if text:
        pyautogui.write(text)
        print(f"⌨️ 입력됨: {text}")
    if tab_after:
        pyautogui.press("tab")
        print("➡️ 탭키 전환됨")
    return x, y
