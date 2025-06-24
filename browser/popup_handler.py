from __future__ import annotations

import datetime
import time
from playwright.sync_api import Page
from popup_text_handler import handle_popup_by_text

import utils

# 마지막으로 처리된 dialog 메시지 저장용
_last_dialog_message: str | None = None

# 메시지 차단 감지용 선택자 목록
BLOCK_SELECTORS = [
    "text=이 페이지가 추가적인 대화를 생성하지 않도록 차단되었습니다",
    "div:has-text('차단되었습니다')",
]


def dialog_blocked(page: Page) -> bool:
    """Return True if Chrome shows the 'dialog blocked' message."""
    for frame in [page, *page.frames]:
        for sel in BLOCK_SELECTORS:
            try:
                loc = frame.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    return True
            except Exception:
                continue
    return False


def is_logged_in(page: Page) -> bool:
    """Return ``True`` if the main menu after login is visible.

    The ``#topMenu`` element is waited for up to 10 seconds. If it isn't
    found, frames are also searched. When ``#loginForm`` is still visible the
    login is treated as failed, otherwise we log a warning and regard the login
    as succeeded even though the menu failed to load.
    """

    try:
        page.wait_for_selector("#topMenu", timeout=10000)
        return True
    except Exception:
        utils.log("#topMenu 직접 탐색 실패, 프레임 탐색 시도")
        for frame in page.frames:
            try:
                if frame.locator("#topMenu").is_visible():
                    utils.log("✅ topMenu 프레임 내에서 감지됨")
                    return True
            except Exception:
                continue
        try:
            if page.locator("#loginForm").is_visible(timeout=500):
                return False
        except Exception:
            pass
        utils.log("⚠️ 메뉴 로딩 실패 - 로그인은 성공으로 간주")
        return True


def register_dialog_handler(page: Page) -> None:
    """Register a one-time dialog handler with error protection."""

    def safe_accept(dialog) -> None:
        global _last_dialog_message
        try:
            msg = dialog.message
            if _last_dialog_message == msg:
                utils.log("⚠️ 중복 다이얼로그 무시")
                return
            _last_dialog_message = msg
            utils.log(f"🟡 다이얼로그 감지됨: '{msg}'")
            dialog.accept()
        except Exception as e:  # pragma: no cover - logging only
            utils.log(f"❌ 다이얼로그 처리 실패 또는 중복 처리 시도됨: {e}")

    try:
        page.once("dialog", safe_accept)
    except Exception as e:  # pragma: no cover - logging only
        utils.log(f"❌ dialog 핸들러 등록 실패: {e}")


def setup_dialog_handler(page: Page, auto_accept: bool = True) -> None:
    """Register a dialog handler once to auto process common dialogs."""

    if getattr(page, "_dialog_handler_registered", False):
        return

    def _handle(dialog) -> None:
        global _last_dialog_message
        logout_keywords = ["종료 하시겠습니까", "로그아웃", "세션 종료"]
        try:
            msg = dialog.message
            if _last_dialog_message == msg:
                utils.log("⚠️ 중복 다이얼로그 무시")
                return
            _last_dialog_message = msg
            if any(kw in msg for kw in logout_keywords):
                try:
                    dialog.dismiss()
                except Exception:
                    pass
                utils.log(f"⚠️ 로그아웃 관련 다이얼로그 무시: {msg}")
                return
            if "차단되었습니다" in msg:
                try:
                    dialog.dismiss()
                except Exception:
                    pass
                utils.log("❌ '추가 대화 차단' 다이얼로그 감지")
                raise RuntimeError("Dialog blocked by browser")
            if auto_accept:
                dialog.accept()
            else:
                try:
                    dialog.dismiss()
                except Exception as e:
                    utils.log(f"dialog.dismiss 오류: {e}")
            utils.log(f"자동 다이얼로그 처리: {msg}")
        except Exception as e:
            utils.log(f"다이얼로그 처리 오류: {e}")

    page.on("dialog", _handle)
    setattr(page, "_dialog_handler_registered", True)




def close_detected_popups(page: Page, loops: int = 2, wait_ms: int = 500) -> bool:
    """Close visible popups using event based waits."""
    register_dialog_handler(page)
    selectors = [
        "text=닫기",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='close']",
        "[id*='close']",
        "div[id*='btn_close']",
        "button:has-text('✕')",
        "text=✕",
    ]

    loops = max(2, loops)
    closed_any = False
    for _ in range(loops):
        found = False
        if handle_popup_by_text(page):
            found = True
            closed_any = True
            time.sleep(wait_ms / 1000)
            continue
        for frame in [page, *page.frames]:
            if hasattr(frame, "is_detached") and frame.is_detached():
                continue
            for sel in selectors:
                try:
                    locs = frame.locator(sel)
                except Exception as e:
                    utils.log(f"선택자 오류({sel}): {e}")
                    continue
                for i in range(locs.count()):
                    btn = locs.nth(i)
                    if not btn.is_visible():
                        continue
                    try:
                        frame.once("dialog", lambda d: d.accept())
                        with frame.expect_popup(timeout=500) as pop:
                            btn.click(timeout=0)
                        if pop.value:
                            pop.value.close()
                        frame.wait_for_timeout(3000)
                        utils.log("⏱️ 팝업 닫기 후 3초간 안정화 대기")
                        found = True
                        closed_any = True
                    except Exception:
                        continue
        if not found:
            break
        time.sleep(wait_ms / 1000)

    if not closed_any:
        # 팝업 버튼 탐색 실패 시 추가로 div/button 검색 시도
        alt_selectors = ["div[id*='btn_close']", "div:has-text('닫기')", "button:has-text('닫기')"]
        for sel in alt_selectors:
            try:
                locs = page.locator(sel)
            except Exception:
                continue
            for i in range(locs.count()):
                btn = locs.nth(i)
                if btn.is_visible():
                    try:
                        btn.click(timeout=0)
                        closed_any = True
                        break
                    except Exception:
                        continue
            if closed_any:
                break


    for frame in [page, *page.frames]:
        for sel in selectors:
            try:
                locs = frame.locator(sel)
            except Exception:
                continue
            for i in range(locs.count()):
                if locs.nth(i).is_visible():
                    utils.popup_handled = False
                    return False
    utils.popup_handled = True
    if closed_any:
        utils.log("✅ 팝업 처리 완료")
    return closed_any
