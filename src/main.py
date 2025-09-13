import sys
import time

import requests
from loguru import logger
from pydantic import AnyUrl, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

STOCK_CSS_SELECTOR = "div#purchaseBox span.status"
STOCK_TEXT_AVAILABLE = "在庫あり"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    SLACK_WEBHOOK_URL: AnyUrl
    MY_USER_ID: str
    TARGET_URL: AnyUrl


class Checker:
    def __init__(self) -> None:
        try:
            self._settings = Settings()
        except ValidationError:
            logger.error(f"Failed to load .env file.")
            sys.exit(1)

        logger.info(self._settings.model_dump())

        options = Options()
        # No window
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

    def _send_slack_message(self, message: str) -> None:
        payload = {"text": f"<@{self._settings.MY_USER_ID}> {message}"}
        requests.post(str(self._settings.SLACK_WEBHOOK_URL), json=payload)

    def run(self) -> None:
        try:
            while True:
                self._driver.get(str(self._settings.TARGET_URL))

                try:
                    # Wait until the element is present.
                    wait_s = WebDriverWait(self._driver, 10)
                    status_elem = wait_s.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, STOCK_CSS_SELECTOR)
                        )
                    )
                    status_text = status_elem.text.strip()

                    logger.info(f"Stock status: {status_text}")

                    if STOCK_TEXT_AVAILABLE in status_text:
                        self._send_slack_message(
                            f"Stock Available!\n{self._settings.TARGET_URL}"
                        )
                        break
                except Exception as e:
                    logger.error(f"Failed to retrieve stock information: {e}")
                    self._send_slack_message(
                        f"Failed to retrieve stock information: {e}"
                    )

                # Wait for 20s.
                time.sleep(20)
        finally:
            self._driver.quit()


def main() -> None:
    Checker().run()


if __name__ == "__main__":
    main()
