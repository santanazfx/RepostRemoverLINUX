import shutil
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType


def start_driver(headless: bool = False):
    """Abre Brave no Linux ou Chrome nos demais sistemas."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if headless:
        options.add_argument("--headless=new")

    chrome_type = ChromeType.GOOGLE
    if sys.platform.startswith("linux"):
        brave_binary = next(
            (
                path
                for name in (
                    "brave-browser",
                    "brave-browser-beta",
                    "brave-browser-nightly",
                )
                if (path := shutil.which(name))
            ),
            None,
        )
        if brave_binary is None:
            raise FileNotFoundError(
                "Brave não foi encontrado no PATH. Instale o Brave e confirme "
                "que o comando 'brave-browser' está disponível."
            )
        options.binary_location = brave_binary
        chrome_type = ChromeType.BRAVE

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager(chrome_type=chrome_type).install()),
        options=options,
    )
    driver.get("https://www.tiktok.com")
    return driver
