import datetime
from pathlib import Path
from playwright.sync_api import Page, expect
from utils import popups_handled, log


def set_month_date_range(page: Page) -> tuple[str, str]:
    """Set the from/to date fields to the first day of this month through today."""
    today = datetime.date.today()
    start = today.replace(day=1)
    start_str = start.strftime("%Y-%m-%d")
    end_str = today.strftime("%Y-%m-%d")

    start_input = page.locator("input[id$='calFromDay.calendaredit:input']")
    if start_input.count() > 0:
        start_input.click()
        start_input.fill(start_str)
        start_input.press("Enter")

    end_input = page.locator("input[id$='calToDay.calendaredit:input']")
    if end_input.count() > 0:
        end_input.click()
        end_input.fill(end_str)
        end_input.press("Enter")

    return start_str, end_str


def extract_sales_detail(page: Page) -> Path:
    """Extract daily sales details for each middle category."""
    if not popups_handled():
        raise RuntimeError("팝업 처리가 완료되지 않아 데이터 추출을 중단합니다")

    log("🟡 날짜 설정 시작")
    start_str, end_str = set_month_date_range(page)

    search_btn = page.locator("div.nexacontentsbox:has-text('조 회')")
    if search_btn.count() > 0:
        search_btn.first.click()
        page.wait_for_load_state("networkidle")
    else:
        log("⚠️ 조회 버튼을 찾을 수 없습니다")

    left_rows = page.locator("div[class^='gridrow_'] .cell_0_0")
    row_count = left_rows.count()

    output_dir = Path(__file__).resolve().parent
    file_name = f"중분류상세매출_{end_str}.txt"
    out_path = output_dir / file_name

    log("🟡 중분류별 매출 상세 추출 시작")
    total_details = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i in range(row_count):
            row = left_rows.nth(i)
            code = row.inner_text().strip()
            row.click()
            expect(page.locator("#gdDetail div[class^='gridrow_']")).to_be_visible(timeout=3000)

            container = page.locator("div[id*='gdDetail']")
            details = page.locator("#gdDetail div[class^='gridrow_']")
            if container.count() == 0 or details.count() == 0:
                log("❌ 상세 테이블 항목 없음")
                continue

            detail_count = details.count()
            total_details += detail_count
            f.write(f"[중분류: {code}]\n")
            for j in range(detail_count):
                d_row = details.nth(j)
                text = d_row.inner_text().replace("\n", "\t").strip()
                if text:
                    f.write(text + "\n")
            f.write("\n")

    if total_details > 0:
        log(f"✅ 매출상세 데이터 저장 → {out_path}")
    return out_path
