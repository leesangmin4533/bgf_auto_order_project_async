import time
import datetime
from playwright.sync_api import Page, TimeoutError
import utils
from .popup_handler import setup_dialog_handler as _setup_dialog_handler


def remove_overlay(page: Page, selector: str = "#nexacontainer", timeout: int = 3000) -> None:
    """Wait for overlay to disappear and remove it if still visible."""
    try:
        overlay = page.locator(selector)
        if overlay.count() > 0 and overlay.first.is_visible():
            try:
                overlay.first.wait_for(state="hidden", timeout=timeout)
            except TimeoutError:
                utils.log(f"❗ 오버레이 계속 표시되어 remove() 시도: {selector}")
                try:
                    overlay.evaluate("el => el.remove()")
                except Exception as e:  # pragma: no cover - logging only
                    utils.log(f"오버레이 제거 실패: {e}")
    except Exception as e:  # pragma: no cover - logging only
        utils.log(f"오버레이 감지 오류: {e}")


def setup_dialog_handler(page: Page, accept: bool = True) -> None:
    """Attach a dialog handler that automatically accepts or dismisses dialogs."""
    _setup_dialog_handler(page, auto_accept=accept)


def close_popup_windows(page: Page, timeout: int = 1000) -> None:
    """Close popup windows spawned from the current page."""
    while True:
        try:
            popup = page.wait_for_event("popup", timeout=timeout).value
            popup.wait_for_load_state()
            popup.close()
            utils.log("새 창 팝업 닫힘")
        except TimeoutError:
            break


def close_all_popups_event(page: Page, loops: int = 2, wait_ms: int = 500) -> bool:
    """Search and close popups using event based waits."""
    selectors = [
        "text=닫기",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='close']",
        "[id*='close']",
    ]

    for _ in range(max(2, loops)):
        found = False
        remove_overlay(page)
        for sel in selectors:
            try:
                locs = page.locator(sel)
            except Exception as e:
                utils.log(f"선택자 오류({sel}): {e}")
                continue
            for i in range(locs.count()):
                btn = locs.nth(i)
                if not btn.is_visible():
                    continue
                try:
                    page.once("dialog", lambda d: d.accept())
                    with page.expect_popup(timeout=500) as pop:
                        btn.click(timeout=0)
                    if pop.value:
                        pop.value.close()
                    found = True
                except Exception as e:
                    utils.log(f"닫기 버튼 클릭 실패: {e}")
                    try:
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        page.screenshot(path=f"popup_error_{ts}.png")
                    except Exception:
                        pass
                    remove_overlay(page)
        close_popup_windows(page, timeout=500)
        if not found:
            break
        page.wait_for_timeout(wait_ms)

    # verify no popups remain
    for sel in selectors:
        try:
            locs = page.locator(sel)
        except Exception:
            continue
        for i in range(locs.count()):
            if locs.nth(i).is_visible():
                utils.popup_handled = False
                return False
    utils.popup_handled = True
    return True


def close_layer_popup(
    page: Page,
    popup_selector: str,
    close_selector: str,
    *,
    timeout: int = 5000,
) -> bool:
    """Close a specific layer popup using event based wait.

    Parameters
    ----------
    page : Page
        Playwright page instance.
    popup_selector : str
        Selector that identifies the popup container.
    close_selector : str
        Selector for the popup close button.
    timeout : int, optional
        Maximum waiting time in milliseconds. Default is 5000.

    Returns
    -------
    bool
        ``True`` if the popup was closed or not visible, ``False`` on timeout
        or error.
    """
    try:
        layer = page.locator(popup_selector)
        if layer.count() == 0 or not layer.first.is_visible():
            return True

        remove_overlay(page)

        selectors = [
            close_selector,
            "text=닫기",
            "button:has-text('닫기')",
            "a:has-text('닫기')",
            "[class*='close']",
        ]
        clicked = False
        for sel in selectors:
            try:
                btn = page.locator(sel)
                if btn.count() > 0 and btn.first.is_visible():
                    page.once("dialog", lambda d: d.accept())
                    with page.expect_popup(timeout=500) as pop_info:
                        btn.first.click()
                    if pop_info.value:
                        pop_info.value.close()
                    clicked = True
                    break
            except Exception as e:
                utils.log(f"닫기 버튼 탐색 오류({sel}): {e}")
        if not clicked:
            utils.log(f"❌ 닫기 버튼을 찾지 못했습니다: {close_selector}")

        try:
            layer.first.wait_for(state="hidden", timeout=timeout)
            utils.log("✅ 레이어 팝업 닫힘")
            return True
        except TimeoutError:
            utils.log("❌ 레이어 팝업 닫기 시간 초과")
            try:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                page.screenshot(path=f"layer_popup_error_{ts}.png")
            except Exception:
                pass
            return False
    except Exception as e:  # pragma: no cover - logging only
        utils.log(f"레이어 팝업 처리 오류: {e}")
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            page.screenshot(path=f"layer_popup_error_{ts}.png")
        except Exception:
            pass
        return False

from .popup_handler import close_detected_popups

def close_all_popups(page: Page, loops: int = 3) -> bool:
    """Unified popup closing routine."""
    success = close_all_popups_event(page, loops=loops)
    if not success:
        success = close_detected_popups(page, loops=loops)
    if not success:
        try:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            page.screenshot(path=f"popup_fail_{ts}.png")
        except Exception:
            pass
        utils.log("❌ 팝업 처리 실패")
    return success
