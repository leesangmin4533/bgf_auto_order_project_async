from playwright.sync_api import Page
from utils import log

POPUP_RULES = [
    {
        "contains": ["재택 유선권장 안내"],
        "selector": "div[id$='btn_close:icontext']",
        "action": lambda page, sel: page.click(sel),
    },
    {
        "contains": ["비밀번호를 입력"],
        "selector": "dialog",
        "action": lambda page, sel: page.on("dialog", lambda d: d.accept()),
    },
    {
        "contains": ["세션이 만료"],
        "selector": "body",
        "action": lambda page, sel: page.reload(),
    },
]

EXCLUDE_TEXTS = ["Copyright", "BGF Retail"]


def handle_popup_by_text(page: Page) -> bool:
    try:
        popup_title = page.locator("div[id$='Static00:text']").inner_text(timeout=1000)
    except Exception:
        log("팝업 제목 탐지 실패")
        return False

    if any(ex in popup_title for ex in EXCLUDE_TEXTS):
        log("⏩ 제외 팝업으로 판단 - 무시")
        return False

    for rule in POPUP_RULES:
        if any(keyword in popup_title for keyword in rule["contains"]):
            log(f"📌 팝업 탐지됨: '{popup_title}' → 규칙 적용")
            try:
                rule["action"](page, rule["selector"])
                return True
            except Exception as e:
                log(f"❌ 팝업 닫기 실패: {e}")
                return False

    log(f"⚠️ 팝업 규칙 없음: '{popup_title}'")
    return False
