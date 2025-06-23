import os
import json
import time
import subprocess
import datetime
import pyautogui
import pygetwindow as gw
from playwright.sync_api import Page

# 팝업 처리 상태를 추적하기 위한 전역 변수
EXPECTED_POPUPS = 2
_closed_popups = 0
_processed_popups = False
# 팝업 닫기 실패가 연속 발생한 횟수
_popup_failure_count = 0


def log(msg: str) -> None:
    """Print a log message with current time."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def popups_handled() -> bool:
    """Return ``True`` if expected popups were already closed."""
    return _closed_popups >= EXPECTED_POPUPS

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


def fallback_close_popups(page: Page) -> None:
    """Alternative popup closing strategy using ESC key and element removal."""
    log("⬇️ 팝업 강제 종료 전략 실행")
    try:
        for frame in [page, *page.frames]:
            frame.hover("body")
            frame.keyboard.press("Escape")
            frame.wait_for_timeout(300)
        divs = page.locator("div[style*='z-index']")
        for i in range(divs.count()):
            d = divs.nth(i)
            if d.is_visible():
                try:
                    d.evaluate("e => e.remove()")
                except Exception:
                    pass
    except Exception as e:  # pragma: no cover - logging only
        log(f"강제 팝업 종료 실패: {e}")
    finally:
        log("⬆️ 팝업 강제 종료 전략 완료")


def close_stzz120_popup(page: Page) -> bool:
    """Close the STZZ120_P0 popup by coordinate click if visible."""
    close_btn_id = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_close:icontext"
    )
    selector = f"#{close_btn_id.replace('.', '\\.').replace(':', '\\:')}"
    btn = page.locator(selector)
    if btn.count() > 0 and btn.is_visible():
        page.evaluate("document.getElementById('nexacontainer').style.pointerEvents = 'none'")
        box = btn.bounding_box()
        if box:
            page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            log("✅ 강제 좌표 클릭으로 STZZ120 팝업 닫기 성공")
        else:
            log("⚠️ boundingBox 없음: 강제 클릭 실패")
        page.evaluate("document.getElementById('nexacontainer').style.pointerEvents = ''")
        return True
    else:
        log("ℹ️ STZZ120 팝업 안 보임")
    return False


def close_popups(
    page: Page,
    repeat: int = 4,
    interval: int = 1000,
    final_wait: int = 3000,
    max_wait: int | None = 5000,
    *,
    force: bool = False,
) -> tuple[int, int]:
    """Detect and close popups on the page.

    Parameters
    ----------
    page : Page
        The Playwright page object to operate on.
    repeat : int, optional
        Number of passes to check for popups. Default is 4.
    interval : int, optional
        Delay between passes in milliseconds. Default is 1000.
    final_wait : int, optional
        Extra wait time in milliseconds after handling popups. Default is 3000.
    max_wait : int | None, optional
        Maximum wait time in milliseconds for the overall routine. ``None`` means
        no time limit. Default is ``5000``.
    force : bool, optional
        If ``True``, run the popup routine regardless of current global state.
        Default is ``False``.

    Returns
    -------
    tuple[int, int]
        A tuple of ``(closed_count, detected_count)`` representing how many
        popups were closed and how many close buttons were detected.
    """

    global _closed_popups

    if _closed_popups >= EXPECTED_POPUPS and not force:
        log("✅ 모든 팝업 이미 처리됨, 추가 닫기 생략")
        return 0, 0

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

    page.evaluate("document.getElementById('nexacontainer').style.pointerEvents = 'none'")
    try:
        while True:
            for frame in [page, *page.frames]:
                buttons = frame.locator(selector_str)
                count = buttons.count()
                total_detected += count
                for i in range(count):
                    btn = buttons.nth(i)
                    if btn.is_visible():
                        try:
                            frame.evaluate("document.getElementById('nexacontainer').style.pointerEvents = 'none'")
                            btn.click(timeout=3000)
                            total_closed += 1
                            frame.wait_for_timeout(800)
                        except Exception as e:  # pragma: no cover - simple logging
                            log(f"팝업 닫기 실패: {e}")
                            try:
                                bbox = btn.bounding_box()
                                if bbox:
                                    cx = bbox["x"] + bbox["width"] / 2
                                    cy = bbox["y"] + bbox["height"] / 2
                                    has_overlay = frame.evaluate(
                                        "(x, y, el) => { const o = document.elementFromPoint(x, y); return o && o !== el && !o.contains(el); }",
                                        cx,
                                        cy,
                                        btn,
                                    )
                                    if has_overlay:
                                        log("요소 위에 오버레이가 존재하여 클릭이 차단됨")
                            except Exception:
                                pass
                        finally:
                            frame.evaluate("document.getElementById('nexacontainer').style.pointerEvents = ''")
            attempts += 1
            elapsed = (time.time() - start) * 1000
            if (max_wait is not None and elapsed >= max_wait) or attempts >= repeat:
                break
            page.wait_for_timeout(interval)

    finally:
        page.evaluate("document.getElementById('nexacontainer').style.pointerEvents = ''")

    _closed_popups += total_closed

    log(f"총 {total_closed}개 팝업 닫기, 감지된 버튼 {total_detected}개")
    remaining_after_close = total_detected - total_closed
    if remaining_after_close > 0:
        log(f"⚠️ 닫히지 않은 팝업 버튼 {remaining_after_close}개 존재")
        if remaining_after_close >= 5:
            log("팝업 구조 변경 가능성 있음")
        # gather remaining popup ids for debugging
        unresolved_ids = []
        for frame in [page, *page.frames]:
            buttons = frame.locator(selector_str)
            for i in range(buttons.count()):
                b = buttons.nth(i)
                if b.is_visible():
                    bid = b.get_attribute("id")
                    if bid:
                        unresolved_ids.append(bid)
        if unresolved_ids:
            log("닫히지 않은 팝업 ID: " + ", ".join(unresolved_ids))
            try:
                page.evaluate(f"alert('Unclosed popups: {','.join(unresolved_ids)}')")
            except Exception:
                log("alert 표시 실패")

    global _popup_failure_count

    if remaining_after_close > 0:
        _popup_failure_count += 1
    else:
        _popup_failure_count = 0

    if _popup_failure_count >= 3:
        fallback_close_popups(page)
        _popup_failure_count = 0

    page.wait_for_timeout(final_wait)
    return total_closed, total_detected


def process_popups_once(page: Page, *, force: bool = False) -> bool:
    """Run popup handling only once for the whole program.

    Parameters
    ----------
    page : Page
        Playwright page instance.
    force : bool, optional
        If ``True``, run popup processing even if it already ran once.

    Returns
    -------
    bool
        ``True`` if all detected popups were closed.
    """

    global _processed_popups

    if _processed_popups and not force:
        log("✅ 팝업 탐색 이미 완료됨")
        return popups_handled()

    closed, detected = close_popups(page, repeat=4, interval=1000, max_wait=7000, force=True)
    _processed_popups = True

    remaining = detected - closed
    log(f"닫히지 않은 팝업 수: {remaining}")
    if remaining == 0:
        log("✅ 팝업 처리 완료")
    else:
        log("⚠️ 일부 팝업이 닫히지 않았습니다")

    return remaining == 0
