import os
import signal
import sys

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import log

logger = log.get_logger("driver")

drivers = []


def sigint_handler(sig, frame):
    logger.info("close driver...")
    for driver in drivers:
        try:
            driver.close()
        except:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, sigint_handler)


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.default_content_setting_values": {"notifications": 2}}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--no-sandbox') # required when running as root user. otherwise you would get no sandbox errors.
    # chrome_options.add_argument('--enable-devtools-experiments')
    # chrome_options.add_argument('--force-devtools-available')
    # chrome_options.add_argument('--debug-devtools')

    chrm_caps = webdriver.DesiredCapabilities.CHROME.copy()
    chrm_caps["goog:loggingPrefs"] = {"performance": "ALL"}
    # driver = webdriver.Chrome(executable_path = os.path.realpath('chromedriver'), options=chrome_options, desired_capabilities=chrm_caps)
    driver = webdriver.Remote(
        command_executor="http://192.168.47.100:4444/wd/hub",
        options=chrome_options,
        desired_capabilities=chrm_caps,
    )
    drivers.append(driver)
    return driver
