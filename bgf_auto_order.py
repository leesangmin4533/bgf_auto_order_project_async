import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# Constants for login
URL = "https://store.bgfretail.com"
USER_ID = "46513"
PASSWORD = "1113"  # TODO: replace with secure storage in production

# Sample order list
ORDER_ITEMS = [
    {"name": "새우깡", "code": "88012345", "quantity": 10},
    {"name": "포카칩", "code": "88065432", "quantity": 5},
]

async def login(page):
    await page.goto(URL)
    await page.fill('input[name="userId"]', USER_ID)
    await page.fill('input[name="userPwd"]', PASSWORD)
    await page.click('button:text("LOGIN")')
    await page.wait_for_selector('div:text("(46513) 이천호반베르디움점")', timeout=15000)

async def close_initial_popup(page):
    try:
        popup = page.locator('button:text("닫기")')
        await popup.click(timeout=5000)
    except PlaywrightTimeoutError:
        pass

async def navigate_to_order(page):
    await page.click('div.main_usamenu_r > ul > li:has-text("발주")')
    await page.wait_for_selector('div.pop_tit:text("발주일/중분류 선택")', timeout=15000)

async def select_category(page, category_name):
    row = page.locator(f'tr:has-text("{category_name}")')
    if not await row.is_visible():
        raise RuntimeError(f"카테고리 '{category_name}'을(를) 찾을 수 없습니다.")
    await row.click()
    await page.click('div.pop_wrap button:text("선택")')
    try:
        blocked = page.locator('div.w2p_alert:text("차단되었습니다")')
        await blocked.wait_for(timeout=2000)
        raise RuntimeError("브라우저 차단 팝업 발생")
    except PlaywrightTimeoutError:
        pass
    await page.wait_for_selector('div#grid_itemList', timeout=20000)

async def fill_order(page, items):
    for item in items:
        try:
            row = page.locator(f'tr:has-text("{item["code"]}")')
            if not await row.is_visible():
                print(f"경고: 상품 '{item['name']}'을(를) 찾을 수 없음")
                continue
            qty_input = row.locator('td').nth(5).locator('input')
            await qty_input.fill(str(item['quantity']))
            await page.wait_for_timeout(500)
        except Exception as e:
            print(f"오류: 상품 '{item['name']}' 처리 중 문제 발생 - {e}")

async def submit_order(page):
    await page.click('button:text("발주서전송")')
    page.once('dialog', lambda dialog: asyncio.create_task(dialog.accept()))
    await page.wait_for_selector('div:text("정상적으로 전송되었습니다.")', timeout=30000)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await login(page)
            await close_initial_popup(page)
            await navigate_to_order(page)
            await select_category(page, "과자류")
            await fill_order(page, ORDER_ITEMS)
            await submit_order(page)
            await page.screenshot(path="result_screenshot.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
