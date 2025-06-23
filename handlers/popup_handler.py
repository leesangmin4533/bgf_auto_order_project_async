from __future__ import annotations
import time
from playwright.sync_api import Page
import utils

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


def login_page_visible(page: Page) -> bool:
    """Check if login form fields are visible (session expired)."""
    selectors = [
        "[id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_id:input']",
        "[id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_pw:input']",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return True
        except Exception:
            continue
    return False


def setup_dialog_handler(page: Page, auto_accept: bool = True) -> None:
    """Register a dialog handler that auto processes common dialogs."""

    def _handle(dialog) -> None:
        logout_keywords = ["종료 하시겠습니까", "로그아웃", "세션 종료"]
        try:
            if any(kw in dialog.message for kw in logout_keywords):
                try:
                    dialog.dismiss()
                except Exception:
                    pass
                utils.log(f"⚠️ 로그아웃 관련 다이얼로그 무시: {dialog.message}")
                return
            if "차단되었습니다" in dialog.message:
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
            utils.log(f"자동 다이얼로그 처리: {dialog.message}")
        except Exception as e:
            utils.log(f"다이얼로그 처리 오류: {e}")

    page.on("dialog", _handle)


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


def close_detected_popups(
    page: Page, max_wait_sec: int = 30, max_loops: int = 3
) -> bool:
    """Repeatedly search and close popups until none remain or timeout.

    The routine performs at least two search passes and at most ``max_loops``
    passes to avoid infinite loops.
    """
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
    while loops < max_loops and (time.time() < end or loops < 2):
        if "차단되었습니다" in page.content():
            utils.log("❌ 페이지에서 차단 문구 감지")
            return False
        if dialog_blocked(page):
            utils.log("❌ 브라우저에서 추가 대화 차단 메시지 감지")
            return False
        if login_page_visible(page):
            utils.log("❌ 로그인 페이지로 돌아감 - 세션 만료 추정")
            return False
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
        page.wait_for_timeout(300)
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
