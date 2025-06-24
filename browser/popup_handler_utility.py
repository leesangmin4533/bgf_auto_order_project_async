import datetime
from playwright.sync_api import Page, TimeoutError
import utils
from .popup_handler import (
    setup_dialog_handler as _setup_dialog_handler,
    register_dialog_handler,
)
from . import popup_utils

from popup_text_handler import handle_popup_by_text


def setup_dialog_handler(page: Page, accept: bool = True) -> None:
    """Attach a dialog handler that automatically accepts or dismisses dialogs."""
    _setup_dialog_handler(page, auto_accept=accept)





def close_all_popups_event(page: Page, loops: int = 2, wait_ms: int = 1000) -> bool:
    """Search and close popups using event based waits."""
    register_dialog_handler(page)
    selectors = [
        "text=닫기",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='close']",
        "[id*='close']",
    ]

    closed_any = False
    for _ in range(max(2, loops)):
        found = False
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
                    popup_utils.add_safe_accept_once(page)
                    with page.expect_popup(timeout=500) as pop:
                        btn.click(timeout=0)
                    if pop.value:
                        pop.value.close()
                    page.wait_for_timeout(2000)
                    found = True
                    closed_any = True
                except TimeoutError:
                    utils.log("팝업 이벤트 시간 초과 → 다음으로 진행")
                except Exception as e:
                    utils.log(f"닫기 버튼 클릭 실패: {e}")
                    try:
                        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        page.screenshot(path=f"popup_error_{ts}.png")
                    except Exception:
                        pass
        if not found:
            break
        page.wait_for_timeout(wait_ms)

    if not closed_any:
        ok_selectors = ["text=확인", "button:has-text('확인')", "input[value='확인']"]
        for ok_sel in ok_selectors:
            try:
                ok_btns = page.locator(ok_sel)
            except Exception:
                continue
            for i in range(ok_btns.count()):
                btn = ok_btns.nth(i)
                if btn.is_visible():
                    try:
                        btn.click(timeout=0)
                        page.wait_for_timeout(2000)
                        found = True
                        break
                    except Exception:
                        continue
            if found:
                break

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
                    popup_utils.add_safe_accept_once(page)
                    with page.expect_popup(timeout=500) as pop_info:
                        btn.first.click()
                    if pop_info.value:
                        pop_info.value.close()
                    page.wait_for_timeout(2000)
                    clicked = True
                    break
            except Exception as e:
                utils.log(f"닫기 버튼 탐색 오류({sel}): {e}")
        if not clicked:
            utils.log(f"❌ 닫기 버튼을 찾지 못했습니다: {close_selector}")

        try:
            layer.first.wait_for(state="hidden", timeout=timeout)
            utils.log("✅ 레이어 팝업 닫힘")
            page.wait_for_timeout(2000)
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
    success = False
    if handle_popup_by_text(page):
        utils.log("✅ 팝업 규칙 기반 닫기 완료")
        success = True
    else:
        utils.log("➡️ 규칙 외 팝업 처리 fallback 진행")
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
