# Utility functions for popup handling
from playwright.sync_api import Page
from utils import log
import time

_last_dialog_message: str | None = None


def safe_accept(dialog) -> None:
    """Safely accept dialogs, caching the last message to avoid repeats."""
    global _last_dialog_message
    try:
        msg = dialog.message
        if _last_dialog_message == msg:
            log("⚠️ 중복 다이얼로그 무시")
            return
        _last_dialog_message = msg
        log(f"🟡 다이얼로그 감지됨: '{msg}'")
        try:
            dialog.accept()
        except Exception as e:
            log(f"dialog.accept 실패: {e}")
        time.sleep(2)
    except Exception as e:  # pragma: no cover - logging only
        log(f"❌ 다이얼로그 처리 실패 또는 중복 처리 시도됨: {e}")


def add_safe_accept_once(page: Page) -> None:
    """Attach ``safe_accept`` once to the given page."""
    try:
        page.once("dialog", safe_accept)
    except Exception as e:  # pragma: no cover - logging only
        log(f"❌ dialog 핸들러 등록 실패: {e}")


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

