import time
from playwright.sync_api import Page
import utils


def close_detected_popups(page: Page, max_wait_sec: int = 30) -> bool:
    """Close all visible popups using reliable locator clicks.

    This function repeatedly searches across all frames for visible buttons
    matching common close patterns and clicks them until none remain or
    ``max_wait_sec`` is exceeded.
    """
    selectors = [
        "div:has-text('닫기')",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='btn_close']",
        "[id*='close']",
        "button:has-text('✕')",
        "text=✕",
    ]

    end = time.time() + max_wait_sec
    checks = 0
    while time.time() < end:
        found = False
        targets = [page, *page.frames]
        for frame in targets:
            if hasattr(frame, "is_detached") and frame.is_detached():
                continue
            for sel in selectors:
                try:
                    locs = frame.locator(sel)
                except Exception as e:  # pragma: no cover - logging only
                    utils.log(f"선택자 오류({sel}): {e}")
                    continue
                for i in range(locs.count()):
                    btn = locs.nth(i)
                    if btn.is_visible():
                        try:
                            btn.click(timeout=0)
                            frame.wait_for_timeout(300)
                            found = True
                        except Exception as e:  # pragma: no cover - logging only
                            utils.log(f"닫기 버튼 클릭 실패: {e}")
        checks += 1
        # 확인 후 여전히 보이는 닫기 버튼이 없으면 종료
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
