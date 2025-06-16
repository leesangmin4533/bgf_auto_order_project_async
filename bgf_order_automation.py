import asyncio
import json
import csv
import logging
import os
import sys
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Page, Locator

# ===============================================================================
# 1. 초기 설정 및 상수 정의
# ===============================================================================

# --- 사용자 설정 변수 ---
# 로그인에 필요한 아이디와 비밀번호는 환경 변수에서 읽어옵니다.
BGF_USER_ID = os.environ.get("BGF_USER_ID")
BGF_USER_PW = os.environ.get("BGF_USER_PW")

# 발주 추천 기준이 되는 안전 재고 수량
SAFETY_STOCK_THRESHOLD = 5

# --- 시스템 설정 변수 ---
LOGIN_URL = "https://store.bgfretail.com/websrc/deploy/index.html"
OUTPUT_FILENAME_JSON = "recommended_orders.json"
OUTPUT_FILENAME_CSV = "recommended_orders.csv"
LOG_FILENAME = "automation.log"

# --- 웹사이트 요소 선택자 (Selector) ---
ID_INPUT_SELECTOR = "#userId"
PW_INPUT_SELECTOR = "#userPwd"
LOGIN_BUTTON_SELECTOR = ".btn_login"
POPUP_CLOSE_BUTTON_SELECTOR = "#notice-popup-close-button"
ORDER_MENU_SELECTOR = 'a:has-text("발주관리")'
INTEGRATED_ORDER_SUBMENU_SELECTOR = 'a:has-text("통합발주")'
QUERY_BUTTON_SELECTOR = 'button:has-text("조회")'
CATEGORY_MODAL_SELECTOR = "#category-selection-modal"
CATEGORY_LIST_ITEM_SELECTOR = ".category-item"
PRODUCT_GRID_SELECTOR = "#productGrid"
PRODUCT_GRID_ROWS_SELECTOR = f"{PRODUCT_GRID_SELECTOR} tbody tr"
LOADING_INDICATOR_SELECTOR = ".loading-spinner"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILENAME, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ===============================================================================
# 2. 핵심 기능 함수 정의
# ===============================================================================

async def login(page: Page) -> bool:
    """BGF Retail 스토어 사이트에 로그인 (디버그 정보 포함)"""
    if not BGF_USER_ID or not BGF_USER_PW:
        logging.error("환경 변수 BGF_USER_ID와 BGF_USER_PW가 설정되어 있지 않습니다.")
        return False

    logging.info(f"로그인 페이지 이동 중: {LOGIN_URL}")
    try:
        await page.goto(LOGIN_URL, timeout=30000)
        await page.wait_for_load_state("networkidle")

        # 1. ID 필드 상태 확인
        try:
            id_input = page.locator("#userId")
            await id_input.wait_for(state="visible", timeout=15000)
            id_enabled = await id_input.is_enabled()
            id_editable = await id_input.is_editable()
            logging.info(f"[userId] visible=True, enabled={id_enabled}, editable={id_editable}")
        except Exception as e:
            logging.error(f"[userId] 필드 탐지 실패: {e}")
            await page.screenshot(path="error_userId_not_found.png")
            return False

        # 2. 입력 시도 전 상태 저장
        await page.screenshot(path="before_fill_userId.png")

        # 3. 키보드 방식으로 ID 입력
        await id_input.click()
        await page.keyboard.insert_text(BGF_USER_ID)
        await page.screenshot(path="after_fill_userId.png")

        # 4. PW 필드 상태 확인
        try:
            pw_input = page.locator("#userPwd")
            await pw_input.wait_for(state="visible", timeout=10000)
            pw_enabled = await pw_input.is_enabled()
            pw_editable = await pw_input.is_editable()
            logging.info(f"[userPwd] visible=True, enabled={pw_enabled}, editable={pw_editable}")
        except Exception as e:
            logging.error(f"[userPwd] 필드 탐지 실패: {e}")
            await page.screenshot(path="error_userPwd_not_found.png")
            return False

        # 5. 비밀번호 입력
        await pw_input.click()
        await page.keyboard.insert_text(BGF_USER_PW)
        await page.screenshot(path="after_fill_userPwd.png")

        # 6. 로그인 버튼 클릭
        await page.wait_for_selector(".btn_login", state="visible", timeout=10000)
        await page.click(".btn_login")
        await page.screenshot(path="after_login_click.png")

        # 7. 로그인 후 메뉴 도착 확인
        await page.wait_for_selector(ORDER_MENU_SELECTOR, timeout=20000)
        logging.info("로그인 성공. 메뉴 확인됨.")

        # 초기 공지 팝업이 존재하면 닫는다.
        try:
            popup_close_button = page.locator(POPUP_CLOSE_BUTTON_SELECTOR)
            if await popup_close_button.is_visible(timeout=5000):
                await popup_close_button.click()
                await page.wait_for_selector(POPUP_CLOSE_BUTTON_SELECTOR, state='hidden', timeout=5000)
        except PlaywrightTimeoutError:
            pass
        except Exception as e:
            logging.warning(f"초기 팝업 처리 중 오류 발생: {e}")

        return True

    except PlaywrightTimeoutError as e:
        logging.error(f"타임아웃 발생: {e}")
        await page.screenshot(path="timeout_error.png")
        return False
    except Exception as e:
        logging.exception(f"로그인 중 예외 발생: {e}")
        await page.screenshot(path="unknown_login_error.png")
        return False

async def navigate_to_integrated_order(page: Page) -> bool:
    """로그인 후 '통합 발주' 페이지로 이동"""
    try:
        await page.wait_for_selector(ORDER_MENU_SELECTOR, timeout=10000)
        await page.click(ORDER_MENU_SELECTOR)
        await page.wait_for_selector(INTEGRATED_ORDER_SUBMENU_SELECTOR, state='visible', timeout=10000)
        await page.click(INTEGRATED_ORDER_SUBMENU_SELECTOR)
        await page.wait_for_selector(QUERY_BUTTON_SELECTOR, timeout=15000)
        await page.click(QUERY_BUTTON_SELECTOR)
        await page.wait_for_selector(CATEGORY_MODAL_SELECTOR, state='visible', timeout=10000)
        return True
    except PlaywrightTimeoutError as e:
        logging.error(f"통합발주 페이지 이동 또는 모달 활성화 중 타임아웃 발생: {e}")
        return False
    except Exception as e:
        logging.exception(f"통합발주 페이지 이동 중 예상치 못한 오류 발생: {e}")
        return False

async def parse_product_row(row: Locator) -> dict | None:
    """상품 테이블의 한 행(row)에서 상품 정보를 파싱"""
    try:
        cells = row.locator('td')
        if cells.count() < 5:
            logging.warning("Skipping row due to insufficient cell count.")
            return None

        product_code = await cells.nth(0).inner_text()
        product_name = await cells.nth(1).inner_text()
        stock_str = await cells.nth(2).inner_text()
        price_str = await cells.nth(3).inner_text()
        available_qty_str = await cells.nth(4).inner_text()

        def clean_and_convert_to_int(text: str) -> int:
            cleaned_text = "".join(filter(str.isdigit, text))
            return int(cleaned_text) if cleaned_text else 0

        return {
            "productCode": product_code.strip(),
            "productName": product_name.strip(),
            "stockQuantity": clean_and_convert_to_int(stock_str),
            "price": clean_and_convert_to_int(price_str),
            "availableQuantity": clean_and_convert_to_int(available_qty_str)
        }
    except Exception as e:
        row_text = "N/A"
        try:
            row_text = (await row.inner_text())[:100] + "..."
        except Exception:
            pass
        logging.warning(f"테이블 행 파싱 중 오류 발생: {e}. 행 내용 스니펫: '{row_text}'.")
        return None

async def scrape_all_category_products(page: Page) -> list[dict]:
    """모든 상품 카테고리를 순회하며 상품 데이터를 스크래핑"""
    all_products = []
    try:
        await page.wait_for_selector(CATEGORY_LIST_ITEM_SELECTOR, timeout=10000)
        category_locators = await page.locator(CATEGORY_LIST_ITEM_SELECTOR).all()
        category_names = [await loc.inner_text() for loc in category_locators]

        if not category_names:
            if await page.locator(CATEGORY_MODAL_SELECTOR).is_visible():
                await page.keyboard.press('Escape')
            return []

        for category_name in category_names:
            try:
                await page.click(QUERY_BUTTON_SELECTOR)
                await page.wait_for_selector(CATEGORY_MODAL_SELECTOR, state='visible', timeout=10000)
                category_to_click_selector = f'{CATEGORY_LIST_ITEM_SELECTOR}:has-text("{category_name}")'
                category_to_click = page.locator(category_to_click_selector)
                await category_to_click.wait_for(state='visible', timeout=10000)
                await category_to_click.dblclick()
                await page.wait_for_load_state('networkidle', timeout=20000)
                try:
                    await page.wait_for_selector(LOADING_INDICATOR_SELECTOR, state='hidden', timeout=10000)
                except PlaywrightTimeoutError:
                    pass
                await page.wait_for_selector(PRODUCT_GRID_SELECTOR, timeout=15000)
                product_rows = await page.locator(PRODUCT_GRID_ROWS_SELECTOR).all()
                for row in product_rows:
                    product_data = await parse_product_row(row)
                    if product_data:
                        all_products.append(product_data)
            except PlaywrightTimeoutError as e:
                logging.warning(f"'{category_name}' 카테고리 처리 중 타임아웃: {e}")
                if await page.locator(CATEGORY_MODAL_SELECTOR).is_visible(timeout=1000):
                    await page.keyboard.press('Escape')
                    try:
                        await page.wait_for_selector(CATEGORY_MODAL_SELECTOR, state='hidden', timeout=5000)
                    except PlaywrightTimeoutError:
                        pass
                continue
            except Exception as e:
                logging.exception(f"'{category_name}' 카테고리 처리 중 오류: {e}")
                if await page.locator(CATEGORY_MODAL_SELECTOR).is_visible(timeout=1000):
                    await page.keyboard.press('Escape')
                    try:
                        await page.wait_for_selector(CATEGORY_MODAL_SELECTOR, state='hidden', timeout=5000)
                    except PlaywrightTimeoutError:
                        pass
                continue
        return all_products
    except PlaywrightTimeoutError as e:
        logging.critical(f"전체 카테고리 목록 수집 중 타임아웃: {e}")
        if await page.locator(CATEGORY_MODAL_SELECTOR).is_visible(timeout=1000):
            await page.keyboard.press('Escape')
            try:
                await page.wait_for_selector(CATEGORY_MODAL_SELECTOR, state='hidden', timeout=5000)
            except PlaywrightTimeoutError:
                pass
        return []
    except Exception as e:
        logging.critical(f"상품 데이터 스크래핑 과정에서 오류 발생: {e}")
        if await page.locator(CATEGORY_MODAL_SELECTOR).is_visible(timeout=1000):
            await page.keyboard.press('Escape')
            try:
                await page.wait_for_selector(CATEGORY_MODAL_SELECTOR, state='hidden', timeout=5000)
            except PlaywrightTimeoutError:
                pass
        return []


def apply_order_recommendation(products: list[dict]) -> list[dict]:
    """상품 목록에 발주 추천 로직 적용"""
    recommended_list = []
    if not products:
        logging.info("분석할 상품 데이터가 없습니다.")
        return []

    logging.info("발주 추천 로직을 적용합니다...")
    for product in products:
        try:
            if not all(k in product for k in ["productCode", "productName", "stockQuantity", "price", "availableQuantity"]):
                logging.warning(f"상품 데이터 형식이 올바르지 않아 추천 로직 적용 불가: {product}")
                continue

            current_stock = product.get("stockQuantity", 0)
            available_qty = product.get("availableQuantity", 0)
            price = product.get("price", 0)
            product_code = product.get("productCode", "N/A")
            product_name = product.get("productName", "N/A")

            if current_stock < SAFETY_STOCK_THRESHOLD and available_qty > 0:
                needed_quantity = SAFETY_STOCK_THRESHOLD - current_stock
                recommended_qty = min(needed_quantity, available_qty)
                if recommended_qty > 0:
                    recommended_item = {
                        "productCode": product_code,
                        "productName": product_name,
                        "currentStock": current_stock,
                        "recommendedOrderQuantity": recommended_qty,
                        "price": price,
                        "estimatedAmount": recommended_qty * price,
                        "reason": f"안전 재고({SAFETY_STOCK_THRESHOLD}) 미달 (현재 재고: {current_stock})"
                    }
                    recommended_list.append(recommended_item)
        except Exception as e:
            logging.error(f"상품 '{product.get('productCode', 'N/A')}' 추천 로직 적용 중 오류: {e}")

    logging.info(f"총 {len(recommended_list)}개의 상품에 대한 발주를 추천합니다.")
    return recommended_list

def output_results(recommended_list: list[dict]):
    """추천 결과를 JSON과 CSV 파일로 저장"""
    if not recommended_list:
        logging.info("출력할 추천 발주 목록이 없습니다.")
        return

    logging.info("--- 최종 발주 추천 목록 ---")
    logging.info(f"총 {len(recommended_list)}개의 추천 상품 목록이 생성되었습니다.")

    try:
        with open(OUTPUT_FILENAME_JSON, 'w', encoding='utf-8') as f:
            json.dump(recommended_list, f, ensure_ascii=False, indent=4)
        logging.info(f"추천 목록을 '{OUTPUT_FILENAME_JSON}' 파일로 저장했습니다.")
    except Exception as e:
        logging.exception(f"JSON 파일 저장 중 오류 발생: {e}")

    try:
        with open(OUTPUT_FILENAME_CSV, 'w', newline='', encoding='utf-8-sig') as f:
            if recommended_list:
                writer = csv.DictWriter(f, fieldnames=recommended_list[0].keys())
                writer.writeheader()
                writer.writerows(recommended_list)
        logging.info(f"추천 목록을 '{OUTPUT_FILENAME_CSV}' 파일로 저장했습니다.")
    except Exception as e:
        logging.exception(f"CSV 파일 저장 중 오류 발생: {e}")

# ===============================================================================
# 3. 메인 실행 로직
# ===============================================================================

async def main():
    logging.info("="*50)
    logging.info("BGF Retail 발주 자동화 스크립트를 시작합니다.")
    logging.info("="*50)

    browser = None
    try:
        async with async_playwright() as p:
            logging.info("Playwright 브라우저 실행 (headless=False).")
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            if not await login(page):
                logging.critical("로그인 실패로 스크립트를 종료합니다.")
                return

            if not await navigate_to_integrated_order(page):
                logging.critical("통합발주 페이지 이동 실패로 스크립트를 종료합니다.")
                return

            all_products_data = await scrape_all_category_products(page)
            if not all_products_data:
                logging.warning("스크래핑된 상품 데이터가 없습니다.")
            else:
                logging.info(f"총 {len(all_products_data)}개의 상품 데이터를 수집했습니다.")

            recommended_orders = apply_order_recommendation(all_products_data)
            output_results(recommended_orders)

    except Exception as e:
        logging.critical(f"스크립트 실행 중 오류 발생: {e}")
        logging.exception("전역 오류 상세 정보:")
        if 'page' in locals() and page:
            try:
                logging.info("오류 발생 시점의 스크린샷 저장 시도.")
                await page.screenshot(path='error_screenshot.png')
                logging.info("오류 발생 시점의 스크린샷을 'error_screenshot.png'로 저장했습니다.")
            except Exception as screenshot_e:
                logging.error(f"스크린샷 저장 중 오류 발생: {screenshot_e}")

    finally:
        if browser:
            try:
                logging.info("브라우저를 닫습니다.")
                await browser.close()
                logging.info("브라우저가 닫혔습니다.")
            except Exception as close_e:
                logging.error(f"브라우저 닫기 중 오류 발생: {close_e}")
        logging.info("="*50)
        logging.info("BGF Retail 발주 자동화 스크립트를 종료합니다.")
        logging.info("="*50)

if __name__ == "__main__":
    asyncio.run(main())
