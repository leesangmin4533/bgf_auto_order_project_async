from __future__ import annotations

import datetime
import time
from typing import Iterable

from playwright.sync_api import Page, expect
from .popup_utils import remove_overlay

import utils

# 구조화된 팝업 정의 목록
POPUP_DEFINITIONS = [
    {
        "name": "Generic Popup",
        "container_selector": "div[style*='z-index']",
        "close_selectors": [
            "text=닫기",
            "button:has-text('닫기')",
            "a:has-text('닫기')",
            "[class*='close']",
            "[id*='close']",
            "button:has-text('✕')",
            "text=✕",
        ],
    },
    {
        "name": "STZZ120",
        "container_selector": "div[id*='STZZ120_P0']",
        "close_selectors": [
            "#mainframe\\.HFrameSet00\\.VFrameSet00\\.FrameSet\\.WorkFrame\\.STZZ120_P0\\.form\\.btn_close:icontext",
        ],
    },
    {
        "name": "재택 안내 팝업",
        "container_selector": "#popupDiv",
        "close_selectors": [
            "button:has-text('닫기')",
        ],
    },
]

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


def login_page_visible(page: Page) -> bool:
    """Return ``True`` if the login form is still visible."""
    try:
        return page.locator("#loginForm").is_visible(timeout=1000)
    except Exception:
        return False


def _locators_iter(frame: Page, selectors: Iterable[str]):
    """Yield locators for each selector, ignoring errors."""
    for sel in selectors:
        try:
            loc = frame.locator(sel)
        except Exception:
            continue
        if loc.count() > 0:
            yield sel, loc


def close_all_popups(page: Page, *, max_loops: int = 5, wait_ms: int = 500) -> bool:
    """Close all popups defined in ``POPUP_DEFINITIONS`` until none remain."""

    max_loops = max(2, max_loops)
    loops = 0
    closed_any = False
    while loops < max_loops:
        loops += 1
        found = False
        for definition in POPUP_DEFINITIONS:
            name = definition["name"]
            container_sel = definition["container_selector"]
            close_sels = definition["close_selectors"]
            for frame in [page, *page.frames]:
                try:
                    containers = frame.locator(container_sel)
                except Exception:
                    continue
                for i in range(containers.count()):
                    cont = containers.nth(i)
                    if not cont.is_visible():
                        continue
                    utils.log(f"팝업 감지 → {name}")
                    clicked = False
                    for sel in close_sels:
                        loc = cont.locator(sel)
                        if loc.count() == 0:
                            loc = frame.locator(sel)
                        for _, btn in (
                            (idx, loc.nth(idx)) for idx in range(loc.count())
                        ):
                            if btn.is_visible():
                                try:
                                    btn.click(timeout=0)
                                    utils.log(f"'{name}' 팝업 닫기: {sel}")
                                    closed_any = True
                                    clicked = True
                                    break
                                except Exception as e:
                                    utils.log(f"'{name}' 팝업 닫기 실패({sel}): {e}")
                        if clicked:
                            break
                    if clicked:
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if not found:
            visible = False
            for definition in POPUP_DEFINITIONS:
                sel = definition["container_selector"]
                for frame in [page, *page.frames]:
                    try:
                        loc = frame.locator(sel)
                    except Exception:
                        continue
                    for j in range(loc.count()):
                        if loc.nth(j).is_visible():
                            visible = True
                            break
                    if visible:
                        break
                if visible:
                    break
            if not visible:
                break
        page.wait_for_timeout(wait_ms)
    return closed_any


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
        + [
            "div[class*='nexacontentsbox']:has-text('확인하기')",
            "div[id*='btn_enter']:has-text('확인')",
        ]
    )

    # 로그아웃 유도 팝업 감지 시 자동 클릭 중단
    for frame in [page, *page.frames]:
        for kw in logout_keywords:
            try:
                warning = frame.locator(
                    f"div[class*='nexacontentsbox']:has-text('{kw}')"
                )
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
                        btn_id = btn.get_attribute("id") or ""
                        btn_class = btn.get_attribute("class") or ""
                        utils.log(
                            f"팝업 버튼 감지 → text:'{text}', id:'{btn_id}', class:'{btn_class}', sel:'{sel}'"
                        )
                    except Exception:
                        text = ""
                    if btn.is_visible() and btn.is_enabled():
                        try:
                            btn.click(timeout=0, force=True)
                            expect(btn).not_to_be_visible(timeout=2000)
                            clicked = True
                        except Exception:
                            utils.log(f"텍스트 팝업 닫기 실패: {sel}")
                    else:
                        print("텍스트:", text)
        if not clicked:
            break


def close_detected_popups(page: Page, loops: int = 2, wait_ms: int = 500) -> bool:
    """Close visible popups using event based waits."""
    selectors = [
        "text=닫기",
        "button:has-text('닫기')",
        "a:has-text('닫기')",
        "[class*='close']",
        "[id*='close']",
        "button:has-text('✕')",
        "text=✕",
    ]

    for _ in range(max(2, loops)):
        found = False
        try:
            if not page.locator("#topMenu").is_visible(timeout=1000):
                remove_overlay(page)
        except Exception:
            remove_overlay(page)
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
                        found = True
                    except Exception as e:
                        utils.log(f"닫기 버튼 클릭 실패: {e}")
                        try:
                            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            page.screenshot(path=f"popup_error_{ts}.png")
                        except Exception:
                            pass
                        remove_overlay(page, force=True)
        if not found:
            break
        handle_text_popups(page)
        time.sleep(wait_ms / 1000)

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
    utils.log("✅ 팝업 처리 완료")
    return True
