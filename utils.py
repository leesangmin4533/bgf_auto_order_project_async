import os
import json
import time
import subprocess
import pyautogui
import pygetwindow as gw
from playwright.sync_api import Page

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


def setup_dialog_handler(page, auto_accept: bool = True) -> None:
    """Register a Playwright dialog handler on the given page.

    Parameters
    ----------
    page : playwright.sync_api.Page
        The Playwright page object to attach the dialog listener to.
    auto_accept : bool, optional
        If True (default), automatically call ``accept()`` on dialogs.
        If False, dialogs will be ``dismiss()`` instead.
    """

    def _handle(dialog) -> None:
        try:
            if auto_accept:
                dialog.accept()
            else:
                dialog.dismiss()
            print(f"자동 다이얼로그 처리: {dialog.message}")
        except Exception as e:
            print(f"다이얼로그 처리 오류: {e}")

    page.on("dialog", _handle)


def close_popups(
    page: Page,
    repeat: int = 3,
    interval: int = 1000,
    final_wait: int = 3000,
    max_wait: int | None = 5000,
) -> int:
    """Detect and close popups on the page.

    Parameters
    ----------
    page : Page
        The Playwright page object to operate on.
    repeat : int, optional
        Number of passes to check for popups. Default is 3.
    interval : int, optional
        Delay between passes in milliseconds. Default is 1000.
    final_wait : int, optional
        Extra wait time in milliseconds after handling popups. Default is 3000.
    max_wait : int | None, optional
        Maximum wait time in milliseconds for the overall routine. ``None`` means
        no time limit. Default is ``5000``.

    Returns
    -------
    int
        Total number of popups closed.
    """

    selectors = [
        "div.nexacontentsbox:has-text('닫기')",
        "button[id*='btn_close']",
        "button[class*='btn_close']",
        "button[id*='btnClose']",
        "button[class*='btnClose']",
        "button[id*='close']",
        "button[class*='close']",
        "[role='button'][id*='btn_close']",
        "[role='button'][class*='btn_close']",
        "[role='button'][id*='btnClose']",
        "[role='button'][class*='btnClose']",
        "[role='button'][id*='close']",
        "[role='button'][class*='close']",
        "button:has-text('닫기')",
        "button:has-text('닫습니다')",
        "[role='button']:has-text('닫기')",
        "[role='button']:has-text('닫습니다')",
    ]
    selector_str = ",".join(selectors)

    start = time.time()
    attempts = 0
    total_closed = 0
    total_detected = 0

    while True:
        for frame in [page, *page.frames]:
            buttons = frame.locator(selector_str)
            count = buttons.count()
            total_detected += count
            for i in range(count):
                btn = buttons.nth(i)
                if btn.is_visible():
                    try:
                        btn.click()
                        total_closed += 1
                        frame.wait_for_timeout(800)
                    except Exception as e:  # pragma: no cover - simple logging
                        print(f"팝업 닫기 실패: {e}")
        attempts += 1
        elapsed = (time.time() - start) * 1000
        if (max_wait is not None and elapsed >= max_wait) or attempts >= repeat:
            break
        page.wait_for_timeout(interval)

    print(f"총 {total_closed}개 팝업 닫기, 감지된 버튼 {total_detected}개")
    if total_closed < total_detected:
        print(f"⚠️ 닫히지 않은 팝업 버튼 {total_detected - total_closed}개 존재")

    page.wait_for_timeout(final_wait)
    return total_closed
