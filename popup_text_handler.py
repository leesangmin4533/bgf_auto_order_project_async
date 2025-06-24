from playwright.sync_api import Page
from utils import log
from browser.popup_handler import add_safe_accept_once

POPUP_RULES = [
    {
        "contains": ["재택 유선권장 안내"],
        "selector": "div[id$='btn_close:icontext']",
        "action": lambda page, sel: page.click(sel),
    },
    {
        "contains": ["비밀번호를 입력"],
        "selector": "dialog",
        "action": lambda page, sel: add_safe_accept_once(page),
    },
    {
        "contains": ["세션이 만료"],
        "selector": "body",
        "action": lambda page, sel: page.reload(),
    },
]

EXCLUDE_TEXTS = ["Copyright", "BGF Retail"]


def handle_popup_by_text(page: Page) -> bool:
    target = page
    try:
        loc = page.locator("div[id$='Static00:text']")
        if loc.count() > 0:
            popup_title = loc.first.inner_text(timeout=1000)
        else:
            raise Exception("not found")
    except Exception:
        log("팝업 제목 탐지 실패 → 프레임 탐색")
        popup_title = None
        for frame in page.frames:
            try:
                loc = frame.locator("div[id$='Static00:text']")
                if loc.count() > 0:
                    popup_title = loc.first.inner_text(timeout=1000)
                    target = frame
                    break
            except Exception:
                continue
        if not popup_title:
            return False

    if any(ex in popup_title for ex in EXCLUDE_TEXTS):
        log("⏩ 제외 팝업으로 판단 - 무시")
        return False

    for rule in POPUP_RULES:
        if any(keyword in popup_title for keyword in rule["contains"]):
            log(f"📌 팝업 탐지됨: '{popup_title}' → 규칙 적용")
            try:
                rule["action"](target, rule["selector"])
                target.wait_for_timeout(3000)
                log("⏱️ 팝업 닫기 후 3초간 안정화 대기")
                return True
            except Exception as e:
                log(f"❌ 팝업 닫기 실패: {e}")
                return False

    log(f"⚠️ 팝업 규칙 없음: '{popup_title}'")
    return False
