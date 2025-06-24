import os
import json
import time
import subprocess
import datetime
import traceback
from pathlib import Path
import types
import sys

import pyautogui
import pygetwindow as gw
from playwright.sync_api import sync_playwright, Page
from dotenv import load_dotenv

# ----- 공통 유틸리티 -----
DEFAULT_WAIT_MS = 1000

EXPECTED_POPUPS = 2
_closed_popups = 0
_processed_popups = False
popup_handled = False
_popup_failure_count = 0
_ignore_popup_failure = False


def wait(page: Page, ms: int = DEFAULT_WAIT_MS) -> None:
    """Convenience wrapper for ``page.wait_for_timeout``."""
    page.wait_for_timeout(ms)


def set_ignore_popup_failure(value: bool) -> None:
    global _ignore_popup_failure
    _ignore_popup_failure = value


def log(msg: str, stage: str | None = None) -> None:
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    if stage:
        print(f"[{timestamp}] [{stage}] {msg}")
    else:
        print(f"[{timestamp}] {msg}")


def popups_handled() -> bool:
    return popup_handled or _ignore_popup_failure or _closed_popups >= EXPECTED_POPUPS


def inject_init_cleanup_script(page: Page) -> None:
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

TESSERACT_CMD = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
CHROME_PATH = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
USER_DATA_DIR = r"C:\\Users\\kanur\\AppData\\Local\\Google\\Chrome\\User Data"
PROFILE_NAME = "Default"


def launch_chrome_fullscreen(url: str) -> None:
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
    time.sleep(1)
    windows = gw.getWindowsWithTitle("Chrome")
    if not windows:
        raise RuntimeError("❌ Chrome 창을 찾을 수 없습니다.")
    win = windows[0]
    return win.left, win.top


def load_points(file_name: str) -> dict:
    file_path = os.path.join(os.path.dirname(__file__), file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def click_point(points: dict, point_key: str) -> tuple[int, int]:
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
    x, y = click_point(points, point_key)
    if text:
        pyautogui.write(text)
        print(f"⌨️ 입력됨: {text}")
    if tab_after:
        pyautogui.press("tab")
        print("➡️ 탭키 전환됨")
    return x, y


def setup_dialog_handler(page, auto_accept: bool = True) -> None:
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
            if "차단되었습니다" in dialog.message:
                try:
                    dialog.dismiss()
                except Exception:
                    pass
                log("❌ '추가 대화 차단' 다이얼로그 감지")
                raise RuntimeError("Dialog blocked by browser")
            if auto_accept:
                try:
                    dialog.accept()
                except Exception as e:
                    log(f"dialog.accept 오류: {e}")
            else:
                try:
                    dialog.dismiss()
                except Exception as e:
                    print(f"dialog.dismiss 오류: {e}")
            time.sleep(2)
            print(f"자동 다이얼로그 처리: {dialog.message}")
        except Exception as e:
            print(f"다이얼로그 처리 오류: {e}")

    if getattr(page, "_dialog_handler_registered", False):
        return

    page.on("dialog", _handle)
    setattr(page, "_dialog_handler_registered", True)


def fallback_close_popups(page: Page) -> None:
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
    except Exception as e:
        log(f"강제 팝업 종료 실패: {e}")
    finally:
        log("⬆️ 팝업 강제 종료 전략 완료")


def close_stzz120_popup(page: Page) -> bool:
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

    loops = min(max(2, repeat), 10)
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
                        frame.wait_for_timeout(2000)
                        closed += 1
                        loop_closed += 1
                    except Exception as e:
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
    global popup_handled
    try:
        close_popups(page, repeat=4, interval=1000, force=True)
        close_stzz120_popup(page)
        close_popups(page, repeat=2, interval=1000, force=True)
        popup_handled = not remaining_popup_button_ids(page)
    except Exception as e:
        log(f"팝업 처리 오류: {e}")
        popup_handled = False
    return popup_handled


def process_popups_once(page: Page, *, force: bool = False) -> bool:
    global _processed_popups
    if _processed_popups and not force:
        log("✅ 팝업 탐색 이미 완료됨")
        return popups_handled()

    result = handle_popup(page)
    _processed_popups = True
    return result


def update_instruction_state(step: str, failure: str | None = None) -> None:
    instr_path = Path(__file__).resolve().parent / "instructions" / "codex_instruction.txt"
    if not instr_path.exists():
        return
    try:
        lines = instr_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return
    new_lines = []
    for line in lines:
        if line.startswith("진행단계"):
            new_lines.append(f"진행단계 = {step}")
        elif line.startswith("마지막실패") and failure is not None:
            new_lines.append(f"마지막실패 = {failure}")
        else:
            new_lines.append(line)
    instr_path.write_text("\n".join(new_lines), encoding="utf-8")


def handle_exception(page: Page, context: str, e: Exception) -> None:
    log(f"❌ 예외 발생 - {context}: {str(e)}")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("screenshots", exist_ok=True)
    path = f"screenshots/error_{context}_{timestamp}.png"
    try:
        page.screenshot(path=path)
        log(f"🖼️ 스크린샷 저장됨: {path}")
    except Exception as se:
        log(f"스크린샷 저장 실패: {se}")

# Register this module as 'utils' for compatibility with other modules
_utils_module = types.ModuleType("utils")
for _name, _obj in list(globals().items()):
    if _name.startswith("_"):
        continue
    setattr(_utils_module, _name, _obj)
sys.modules["utils"] = _utils_module

# ----- 로그인 처리 -----
load_dotenv()
ID = os.getenv("LOGIN_ID")
PW = os.getenv("LOGIN_PW")

from browser.popup_handler import is_logged_in


def perform_login(page: Page) -> bool:
    page.goto("https://store.bgfretail.com/websrc/deploy/index.html")

    page.wait_for_selector(
        "#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_id\\:input",
        timeout=10000,
    )
    page.fill(
        "#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_id\\:input",
        ID,
    )
    page.wait_for_timeout(1000)

    page.fill(
        "#mainframe\\.HFrameSet00\\.LoginFrame\\.form\\.div_login\\.form\\.edt_pw\\:input",
        PW,
    )
    page.wait_for_timeout(1000)

    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    if is_logged_in(page):
        log("✅ 로그인 성공")
        return True
    else:
        log("❌ 로그인 실패")
        return False

# ----- 메인 실행 흐름 -----
from order import run_sales_analysis


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        if not perform_login(page):
            browser.close()
            return

        if not process_popups_once(page):
            browser.close()
            return

        if popups_handled() and datetime.datetime.today().weekday() == 0:
            run_sales_analysis(page)

        browser.close()


if __name__ == "__main__":
    main()
