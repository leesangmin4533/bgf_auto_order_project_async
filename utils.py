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
popup_handled = False
# 팝업 닫기 실패가 연속 발생한 횟수
_popup_failure_count = 0
_ignore_popup_failure = False


def set_ignore_popup_failure(value: bool) -> None:
    """Set whether popup failures should be ignored."""
    global _ignore_popup_failure
    _ignore_popup_failure = value


def log(msg: str) -> None:
    """Print a log message with current time."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def popups_handled() -> bool:
    """Return ``True`` if popup handling has succeeded."""
    return popup_handled or _ignore_popup_failure or _closed_popups >= EXPECTED_POPUPS


def inject_init_cleanup_script(page: Page) -> None:
    """Inject a script that removes overlays and closing popups on load."""
    page.add_init_script(
        """
        document.addEventListener("DOMContentLoaded", () => {
            document
                .querySelectorAll(
                    "div.nexamodaloverlay, div.nexacontentsbox:has-text('닫기')"
                )
                .forEach((el) => el.remove());
        });
        """
    )

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
        logout_keywords = ["종료 하시겠습니까", "로그아웃", "세션 종료"]
        try:
            if any(kw in dialog.message for kw in logout_keywords):
                try:
                    dialog.dismiss()
                except Exception:
                    pass
                log(f"⚠️ 로그아웃 관련 다이얼로그 무시: {dialog.message}")
                return
            if auto_accept:
                dialog.accept()
            else:
                try:
                    dialog.dismiss()
                except Exception as e:
                    print(f"dialog.dismiss 오류: {e}")
            print(f"자동 다이얼로그 처리: {dialog.message}")
        except Exception as e:
            print(f"다이얼로그 처리 오류: {e}")

    page.on("dialog", _handle)


def fallback_close_popups(page: Page) -> None:
    """Alternative popup closing strategy using ESC key and element removal."""
    log("⬇️ 팝업 강제 종료 전략 실행")
    try:
        try:
            page.hover("body")
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        except Exception as e:
            log(f"ESC 키 전송 실패: {e}")
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


def force_click_with_timeout(page, element_id: str, max_delay_ms: int = 15000):
    page.evaluate(f'''
        (() => {{
            const el = document.getElementById("{element_id}");
            if (el) {{
                const blocker = document.getElementById("nexacontainer") || document.body;
                const oldStyle = blocker.style.pointerEvents;
                blocker.style.pointerEvents = "none";
                setTimeout(() => {{
                    el.click();
                    blocker.style.pointerEvents = oldStyle;
                }}, {max_delay_ms});
            }}
        }})();
    ''')


def close_popups(
    page: Page,
    repeat: int = 3,
    interval: int = 1000,
    final_wait: int = 3000,
    max_wait: int | None = None,
    *,
    force: bool = False,
) -> tuple[int, int]:
    """Detect and close popups strictly by locator click only.

    Parameters
    ----------
    page : Page
        The Playwright page instance.
    repeat : int, optional
        Number of passes to search for popups. ``repeat`` is forced to be at
        least ``2``.
    interval : int, optional
        Delay in milliseconds between passes. Default is ``1000``.
    final_wait : int, optional
        Extra wait after the routine finishes. Default is ``3000``.
    max_wait : int | None, optional
        If set, maximum time in milliseconds to spend searching for popups.
    force : bool, optional
        If ``True``, run regardless of current popup state.

    Returns
    -------
    tuple[int, int]
        ``(closed_count, detected_count)``
    """

    global _closed_popups, _popup_failure_count

    if _closed_popups >= EXPECTED_POPUPS and not force:
        log("✅ 모든 팝업 이미 처리됨, 추가 닫기 생략")
        return 0, 0

    text_selectors = [
        "text=닫기",
        "text=닫습니다",
        "button:has-text('닫기')",
        "[role='button']:has-text('닫기')",
        "a:has-text('닫기')",
        "[aria-label='닫기']",
        "button:has-text('Close')",
        "[aria-label='close']",
        "button:has-text('✕')",
        "text=✕",
    ]
    attr_selectors = [
        "button[id*='close']",
        "button[class*='close']",
        "a[class*='close']",
        "div[class*='close']",
        "span[class*='close']",
        "[role='button'][id*='close']",
        "[role='button'][class*='close']",
        "button.close",
        "a.close",
        ".btn-close",
        ".modal-close",
        "[data-dismiss='modal']",
    ]
    selectors = text_selectors + attr_selectors

    closed = 0
    detected = 0

    loops = max(2, repeat)
    start = time.time() * 1000
    for _ in range(loops):
        loop_closed = 0
        for frame in [page, *page.frames]:
            if hasattr(frame, "is_detached") and frame.is_detached():
                log("프레임이 분리되어 건너뜀")
                continue
            for sel in selectors:
                try:
                    loc = frame.locator(sel)
                    count = loc.count()
                except Exception as e:
                    log(f"Locator.count 오류({sel}): {e}")
                    continue
                if count == 0:
                    continue
                detected += count
                for i in range(count):
                    btn = loc.nth(i)
                    if not btn.is_visible():
                        continue
                    try:
                        btn.click(timeout=0)
                        frame.wait_for_timeout(300)
                        closed += 1
                        loop_closed += 1
                    except Exception as e:  # pragma: no cover - logging only
                        log(f"팝업 닫기 실패: {e}")
        if loop_closed == 0:
            break
        if max_wait is not None and (time.time() * 1000 - start) >= max_wait:
            log("max_wait 초과로 팝업 탐색 중단")
            break
        page.wait_for_timeout(interval)

    _closed_popups += closed

    remaining_after_close = detected - closed
    if remaining_after_close > 0:
        _popup_failure_count += 1
    else:
        _popup_failure_count = 0

    if _popup_failure_count >= 3:
        fallback_close_popups(page)
        _popup_failure_count = 0

    log(f"총 {closed}개 팝업 닫기, 감지된 버튼 {detected}개")
    page.wait_for_timeout(final_wait)
    return closed, detected


def remaining_popup_button_ids(page: Page) -> list[str]:
    """Return IDs of still visible popup close buttons."""
    text_selectors = [
        "text=닫기",
        "text=닫습니다",
        "button:has-text('닫기')",
        "[role='button']:has-text('닫기')",
        "a:has-text('닫기')",
        "[aria-label='닫기']",
        "button:has-text('Close')",
        "[aria-label='close']",
        "button:has-text('✕')",
        "text=✕",
    ]
    attr_selectors = [
        "button[id*='close']",
        "button[class*='close']",
        "a[class*='close']",
        "div[class*='close']",
        "span[class*='close']",
        "[role='button'][id*='close']",
        "[role='button'][class*='close']",
        "button.close",
        "a.close",
        ".btn-close",
        ".modal-close",
        "[data-dismiss='modal']",
    ]
    selectors = text_selectors + attr_selectors

    ids: list[str] = []
    for frame in [page, *page.frames]:
        if hasattr(frame, "is_detached") and frame.is_detached():
            continue
        for sel in selectors:
            try:
                loc = frame.locator(sel)
                count = loc.count()
            except Exception:
                continue
            for i in range(count):
                btn = loc.nth(i)
                if not btn.is_visible():
                    continue
                btn_id = btn.get_attribute("id")
                if btn_id:
                    ids.append(btn_id)
    return ids


def handle_popup(page: Page) -> bool:
    """Close all popups once and set ``popup_handled`` status."""

    global popup_handled
    try:
        close_popups(page, repeat=4, interval=1000, force=True)
        close_stzz120_popup(page)
        close_popups(page, repeat=2, interval=1000, force=True)
        popup_handled = not remaining_popup_button_ids(page)
    except Exception as e:  # pragma: no cover - logging only
        log(f"팝업 처리 오류: {e}")
        popup_handled = False
    return popup_handled

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

    result = handle_popup(page)
    _processed_popups = True
    return result
