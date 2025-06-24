# Utility functions for popup handling
from playwright.sync_api import Page
from utils import log


def remove_overlay(page: Page, *, force: bool = False) -> None:
    """Wait for overlay to disappear and optionally remove it as a last resort."""

    try:
        overlay = page.locator("#nexacontainer")
        overlay.wait_for(state="hidden", timeout=5000)
    except Exception:
        log("⚠️ 오버레이가 사라지지 않음 - remove()는 사용하지 않음")
        if force:
            try:
                if not page.locator("#topMenu").is_visible(timeout=3000):
                    page.evaluate("document.getElementById('nexacontainer')?.remove()")
                    log("🛠️ 오버레이 강제 제거 수행됨")
            except Exception:
                log("❌ 오버레이 강제 제거 실패")

