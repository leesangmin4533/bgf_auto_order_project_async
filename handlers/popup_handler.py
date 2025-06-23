from __future__ import annotations
import time
from playwright.sync_api import Page
import utils


def handle_text_popups(page: Page) -> None:
    """Click common text-based confirmation buttons in all frames."""
    texts = ["확인", "확인하기"]
    logout_keywords = ["종료 하시겠습니까", "로그아웃", "세션 종료"]
    selectors = (
        [f"div:has-text('{t}')" for t in texts]
        + [f"button:has-text('{t}')" for t in texts]
        + [f"div[class*='nexacontentsbox']:has-text('{t}')" for t in texts]
        + [f"div[id*='btn_enter']:has-text('{t}')" for t in texts]
    )

    # 로그아웃 유도 팝업 감지 시 자동 클릭 중단
    for frame in [page, *page.frames]:
        for kw in logout_keywords:
            try:
                warning = frame.locator(f"div[class*='nexacontentsbox']:has-text('{kw}')")
                if warning.count() > 0 and warning.first.is_visible():
                    utils.log(f"⚠️ 로그아웃 관련 팝업 감지: {kw}")
                    return
            except Exception:
                continue

    for _ in range(2):
        clicked = False
        for frame in [page, *page.frames]:
            if hasattr(frame, "is_detached") and frame.is_detached():
                continue
            for sel in selectors:
                try:
                    loc = frame.locator(sel)
                except Exception:
                    continue
                count = loc.count()
                if count == 0:
                    print("감지된 수:", count)
                for i in range(count):
                    btn = loc.nth(i)
                    try:
                        text = btn.inner_text()
                    except Exception:
                        text = ""
                    if btn.is_visible() and btn.is_enabled():
                        try:
                            btn.click(timeout=0, force=True)
                            frame.wait_for_timeout(300)
                            clicked = True
                        except Exception:
                            utils.log(f"텍스트 팝업 닫기 실패: {sel}")
                    else:
                        print("텍스트:", text)
        if not clicked:
            break


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

    # 디버깅을 위해 현재 페이지의 HTML을 저장
    try:
        with open("popup_debug.html", "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception as e:
        utils.log(f"팝업 디버그 HTML 저장 실패: {e}")

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
