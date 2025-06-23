import json
import datetime
from pathlib import Path
from playwright.sync_api import Page
from utils import popups_handled, log


def extract_middle_category_products(page: Page) -> Path:
    """Extract product codes and names for each middle category.

    Parameters
    ----------
    page : Page
        Playwright page already navigated to the middle category sales page.

    Returns
    -------
    Path
        Path to the saved JSON file.
    """
    if not popups_handled():
        raise RuntimeError("팝업 처리가 완료되지 않았습니다.")

    left_rows = page.locator("div[class^='gridrow_'] .cell_0_0")
    row_count = left_rows.count()

    result: list[dict] = []
    for i in range(row_count):
        row = left_rows.nth(i)
        category = row.inner_text().strip()
        row.click()
        page.wait_for_timeout(500)

        detail_rows = page.locator("#gdDetail div[class^='gridrow_']")
        products: list[dict] = []
        for j in range(detail_rows.count()):
            d_row = detail_rows.nth(j)
            cells = d_row.locator("div")
            if cells.count() >= 2:
                code = cells.nth(0).inner_text().strip()
                name = cells.nth(1).inner_text().strip()
                if code and name:
                    products.append({"code": code, "name": name})
        result.append({"category": category, "products": products})

    output_dir = Path(__file__).resolve().parent
    file_name = f"중분류상품_{datetime.date.today():%Y%m%d}.json"
    out_path = output_dir / file_name
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log(f"✅ 상품코드 및 상품명 저장 → {out_path}")
    return out_path
