import os
import signal

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import log

logger = log.get_logger("driver")

interrupt = False


def interrupted():
    return interrupt


def sig_handler(sig, frame):
    global interrupt
    interrupt = True
    raise Exception("quit driver...")


signal.signal(signal.SIGINT, sig_handler)


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values": {"notifications": 2}}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(
        "--no-sandbox"
    )  # required when running as root user. otherwise you would get no sandbox errors.
    # chrome_options.add_argument("--enable-devtools-experiments")
    # chrome_options.add_argument("--force-devtools-available")
    # chrome_options.add_argument("--debug-devtools")

    chrm_caps = webdriver.DesiredCapabilities.CHROME.copy()
    chrm_caps["goog:loggingPrefs"] = {"performance": "ALL"}
    # driver = webdriver.Chrome(executable_path = os.path.realpath('chromedriver'), options=chrome_options, desired_capabilities=chrm_caps)
    driver = webdriver.Remote(
        command_executor="http://192.168.47.100:4444/wd/hub",
        options=chrome_options,
        desired_capabilities=chrm_caps,
    )
    return driver


def handle_alert(driver, afterfn):
    alert = EC.alert_is_present()(driver)
    if alert:
        logger.info("alert is present: %s", alert.text)
        driver.quit()
        driver = get_driver()
        afterfn(driver)
    return driver
