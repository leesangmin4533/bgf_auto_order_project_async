from __future__ import annotations
import time
from playwright.sync_api import Page
import utils


def handle_text_popups(page: Page) -> None:
    """Click common text-based confirmation buttons in all frames."""
    texts = ["확인", "확인하기"]
    selectors = [f"div:has-text('{t}')" for t in texts] + [f"button:has-text('{t}')" for t in texts]
    for frame in [page, *page.frames]:
        if hasattr(frame, "is_detached") and frame.is_detached():
            continue
        for sel in selectors:
            try:
                loc = frame.locator(sel)
            except Exception:
                continue
            for i in range(loc.count()):
                btn = loc.nth(i)
                if btn.is_visible():
                    try:
                        btn.click(timeout=0)
                        frame.wait_for_timeout(300)
                    except Exception:
                        utils.log(f"텍스트 팝업 닫기 실패: {sel}")


def close_detected_popups(page: Page, max_wait_sec: int = 30) -> bool:
    """Repeatedly search and close popups until none remain or timeout."""
    text_selectors = [
        "text=닫기",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='btn_close']",
        "[id*='close']",
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
    ]
    selectors = text_selectors + attr_selectors

    end = time.time() + max_wait_sec
    checks = 0
    loops = 0
    while time.time() < end or loops < 2:
        found = False
        targets = [page, *page.frames]
        for frame in targets:
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
                    if btn.is_visible():
                        try:
                            btn.click(timeout=0)
                            frame.wait_for_timeout(300)
                            found = True
                        except Exception as e:
                            utils.log(f"닫기 버튼 클릭 실패: {e}")
        handle_text_popups(page)
        checks += 1
        loops += 1
        visible = False
        for frame in targets:
            if hasattr(frame, "is_detached") and frame.is_detached():
                continue
            for sel in selectors:
                try:
                    locs = frame.locator(sel)
                except Exception:
                    continue
                for i in range(locs.count()):
                    if locs.nth(i).is_visible():
                        visible = True
                        break
                if visible:
                    break
            if visible:
                break
        if not visible:
            utils.popup_handled = True
            utils.log(f"✅ 팝업 처리 완료 ({checks}회 확인)")
            return True
        page.wait_for_timeout(3000)
    utils.popup_handled = False
    utils.log("❌ 팝업 닫기 시간 초과")
    return False
