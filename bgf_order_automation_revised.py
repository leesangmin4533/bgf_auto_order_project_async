import logging
import os
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError

load_dotenv()

# --- 로깅 설정 ---
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                               datefmt='%Y-%m-%d %H:%M:%S'))

logger = logging.getLogger()
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(console_handler)

# --- 설정 변수 ---
USER_ID = os.environ.get('BGF_USER_ID', 'YOUR_ID_HERE')
USER_PW = os.environ.get('BGF_USER_PW', 'YOUR_PASSWORD_HERE')

LOGIN_URL = "https://store.bgfretail.com/websrc/deploy/index.html"
ERROR_SCREENSHOT_PATH = "timeout_error.png"

# --- 선택자 (Selectors) ---
ID_SELECTOR = "input[type='text']"
PW_SELECTOR = "input[type='password']"
LOGIN_BUTTON_SELECTOR = "div:has-text('로그인')"
POST_LOGIN_INDICATOR_SELECTOR = 'text="점포매출"'


def run_automation():
    """Playwright를 사용하여 BGF Retail 웹사이트에 로그인"""
    if not USER_ID or not USER_PW or "YOUR_" in USER_ID or "YOUR_" in USER_PW:
        logger.critical("❌ 환경 변수가 누락되었거나 기본값이 설정되어 있습니다.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = None
        page = None
        try:
            logger.info("Playwright 브라우저 실행 (headless=False).")
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            logger.info(f"로그인 페이지 이동 중: {LOGIN_URL}")
            page.goto(LOGIN_URL, timeout=60000)

            logger.info(f"아이디 입력 필드 대기 중... (선택자: {ID_SELECTOR})")
            page.wait_for_selector(ID_SELECTOR, state='visible', timeout=60000)
            logger.info("아이디 입력 중...")
            user_id_field = page.locator(ID_SELECTOR)
            user_id_field.click()
            page.keyboard.insert_text(USER_ID)

            logger.info(f"비밀번호 입력 필드 대기 중... (선택자: {PW_SELECTOR})")
            page.wait_for_selector(PW_SELECTOR, state='visible', timeout=60000)
            logger.info("비밀번호 입력 중...")
            password_field = page.locator(PW_SELECTOR)
            password_field.click()
            page.keyboard.insert_text(USER_PW)

            logger.info(f"로그인 버튼 대기 중... (선택자: {LOGIN_BUTTON_SELECTOR})")
            page.wait_for_selector(LOGIN_BUTTON_SELECTOR, state='visible', timeout=60000)
            logger.info("로그인 버튼 클릭.")
            page.click(LOGIN_BUTTON_SELECTOR)

            logger.info(
                f"로그인 성공 확인 대기 중... (확인 요소: '{POST_LOGIN_INDICATOR_SELECTOR}')"
            )
            page.wait_for_selector(POST_LOGIN_INDICATOR_SELECTOR,
                                  state='visible', timeout=60000)

            logger.info("로그인에 성공했습니다! 메인 페이지로 이동 완료.")

            logger.info("데이터 스크래핑 로직을 실행합니다... (현재는 대기 후 종료)")
            page.wait_for_timeout(5000)

        except TimeoutError as e:
            logger.error("타임아웃 발생: 로그인 과정 중 문제가 발생했습니다.")
            logger.error(f"오류 상세 정보: {str(e).splitlines()[0]}")
            if page:
                try:
                    page.screenshot(path=ERROR_SCREENSHOT_PATH)
                    logger.info(
                        f"오류 발생 시점의 스크린샷을 저장했습니다: {os.path.abspath(ERROR_SCREENSHOT_PATH)}"
                    )
                except Exception as screenshot_e:
                    logger.error(f"스크린샷 저장 중 별도의 오류 발생: {screenshot_e}")
            logger.critical("로그인 실패로 스크립트를 종료합니다.")
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {e.__class__.__name__} - {e}")
            logger.critical("오류로 인해 스크립트를 종료합니다.")
        finally:
            if browser and browser.is_connected():
                logger.info("브라우저를 닫습니다.")
                browser.close()
                logger.info("브라우저가 닫혔습니다.")


def main():
    logger.info("=" * 50)
    logger.info("BGF Retail 발주 자동화 스크립트 (개선 버전)을 시작합니다.")
    logger.info("=" * 50)

    run_automation()

    logger.info("=" * 50)
    logger.info("BGF Retail 발주 자동화 스크립트를 종료합니다.")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
