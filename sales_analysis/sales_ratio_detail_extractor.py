import datetime
from pathlib import Path
from playwright.sync_api import Page
from utils import popups_handled, log


def set_current_month_range(page: Page) -> tuple[str, str]:
    """Set the date range to the first day of this month through today."""
    today = datetime.date.today()
    start = today.replace(day=1)
    start_str = start.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    start_selectors = [
        "input[name='fromDate']",
        "input[name='startDate']",
        "input[id*='frDate']",
        "input[id*='start']",
    ]
    end_selectors = [
        "input[name='toDate']",
        "input[name='endDate']",
        "input[id*='toDate']",
        "input[id*='end']",
    ]
    button_selectors = ["button:has-text('조회')", "a:has-text('조회')"]

    for sel in start_selectors:
        locator = page.locator(sel)
        if locator.count() > 0:
            locator.first.fill(start_str)
            break
    for sel in end_selectors:
        locator = page.locator(sel)
        if locator.count() > 0:
            locator.first.fill(end_str)
            break
    for sel in button_selectors:
        locator = page.locator(sel)
        if locator.count() > 0:
            locator.first.click()
            break
    page.wait_for_load_state("networkidle")
    return start_str, end_str


def extract_sales_ratio_details(page: Page) -> Path:
    """Extract detail table data for all middle categories."""
    if not popups_handled():
        raise RuntimeError("팝업 처리가 완료되지 않았습니다.")

    log("🟡 매출상세 추출을 위한 날짜 범위 설정")
    start_str, end_str = set_current_month_range(page)

    log("🟡 중분류 테이블 파싱 시작")

    left_rows = page.locator("table tr")
    row_count = left_rows.count()

    output_dir = Path(__file__).resolve().parent
    file_name = f"중분류상세매출_{end_str}.txt"
    out_path = output_dir / file_name

    with out_path.open("w", encoding="utf-8") as f:
        for i in range(row_count):
            row = left_rows.nth(i)
            category = row.inner_text().strip()
            row.click()
            page.wait_for_timeout(500)
            details = page.locator("table:has(th:text('상품명')) tr")
            texts = [d.inner_text().strip() for d in details.all()]
            f.write(f"[중분류: {category}]\n")
            for line in texts:
                f.write(line + "\n")
            f.write("\n")
    log(f"✅ 매출상세 데이터 저장 완료 → {out_path}")
    return out_path
