import time
from playwright.sync_api import Page
import utils
from handlers.popup_handler import setup_dialog_handler as _setup_dialog_handler


def setup_dialog_handler(page: Page, accept: bool = True) -> None:
    """Attach a dialog handler that automatically accepts or dismisses dialogs."""
    _setup_dialog_handler(page, auto_accept=accept)


def close_layer_popup(
    page: Page,
    popup_selector: str,
    close_selector: str,
    *,
    timeout: int = 5000,
    check_interval: int = 500,
) -> bool:
    """Close a specific layer popup and wait until it disappears.

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
    check_interval : int, optional
        Interval between visibility checks in milliseconds. Default is 500.

    Returns
    -------
    bool
        ``True`` if the popup was closed or not visible, ``False`` on timeout
        or error.
    """
    try:
        start = time.time()
        layer = page.locator(popup_selector)
        if layer.count() == 0 or not layer.first.is_visible():
            return True
        # Try close button using various selectors
        selectors = [close_selector, "text=닫기", "button:has-text('닫기')", "a:has-text('닫기')"]
        clicked = False
        for sel in selectors:
            try:
                btn = page.locator(sel)
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click()
                    clicked = True
                    break
            except Exception as e:
                utils.log(f"닫기 버튼 탐색 오류({sel}): {e}")
        if not clicked:
            utils.log(f"❌ 닫기 버튼을 찾지 못했습니다: {close_selector}")
        # Wait until popup disappears
        while time.time() - start < timeout / 1000:
            if layer.count() == 0 or not layer.first.is_visible():
                utils.log("✅ 레이어 팝업 닫힘")
                return True
            page.wait_for_timeout(check_interval)
        utils.log("❌ 레이어 팝업 닫기 시간 초과")
        return False
    except Exception as e:  # pragma: no cover - logging only
        utils.log(f"레이어 팝업 처리 오류: {e}")
        return False
