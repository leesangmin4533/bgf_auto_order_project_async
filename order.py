import datetime
from playwright.sync_api import Page
from utils import log, wait
from sales_analysis.navigate_sales_ratio import navigate_sales_ratio
from sales_analysis.extract_sales_detail import extract_sales_detail
from sales_analysis.middle_category_product_extractor import extract_middle_category_products


def run_sales_analysis(page: Page) -> None:
    """Run sales analysis workflow on Mondays."""
    if datetime.datetime.today().weekday() != 0:
        log("오늘은 월요일이 아니므로 매출 분석을 건너뜁니다")
        return

    log("➡️ 매출분석 메뉴 진입 시도")
    wait(page)
    navigate_sales_ratio(page)
    wait(page)
    log("✅ 메뉴 진입 성공")

    log("🟡 매출 상세 데이터 추출 시작")
    wait(page)
    extract_sales_detail(page)
    wait(page)
    extract_middle_category_products(page)
    wait(page)
    log("✅ 매출 상세 데이터 추출 완료")
